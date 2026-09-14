from time import perf_counter
from typing import Any

from langgraph.graph import END, START, StateGraph

from apps.api.agents.router import CheapRouter
from apps.api.agents.state import AgentState
from apps.api.agents.trace import AgentTraceStore
from apps.api.domain.safety.policy import AuthorizedToolCall, SafetyDecision, SafetyPolicyEngine
from apps.api.domain.vehicle.service import VehicleService
from apps.api.models.gateway import ModelGateway, ModelGatewayDisabled, ModelGatewayError
from apps.api.tools.registry import ToolExecutor, ToolRegistry
from apps.api.tools.schemas import ToolCallPlan


class CockpitAgentGraph:
    def __init__(
        self,
        *,
        vehicle_service: VehicleService,
        trace_store: AgentTraceStore,
        model_gateway: ModelGateway,
    ) -> None:
        self._vehicle_service = vehicle_service
        self._trace = trace_store
        self._model = model_gateway
        self._router = CheapRouter()
        self._registry = ToolRegistry()
        self._safety = SafetyPolicyEngine()
        self._executor = ToolExecutor(vehicle_service)
        self.compiled = self._build()

    def _build(self) -> Any:
        graph = StateGraph(AgentState)
        graph.add_node("load_context", self.load_context)
        graph.add_node("route_intent", self.route_intent)
        graph.add_node("model_plan", self.model_plan)
        graph.add_node("validate_tools", self.validate_tools)
        graph.add_node("safety_gate", self.safety_gate)
        graph.add_node("execute_tools", self.execute_tools)
        graph.add_node("compose_response", self.compose_response)
        graph.add_edge(START, "load_context")
        graph.add_edge("load_context", "route_intent")
        graph.add_conditional_edges(
            "route_intent",
            lambda state: state["route"],
            {
                "rule": "validate_tools",
                "vehicle_info": "compose_response",
                "model": "model_plan",
            },
        )
        graph.add_edge("model_plan", "validate_tools")
        graph.add_edge("validate_tools", "safety_gate")
        graph.add_edge("safety_gate", "execute_tools")
        graph.add_edge("execute_tools", "compose_response")
        graph.add_edge("compose_response", END)
        return graph.compile()

    async def load_context(self, state: AgentState) -> dict[str, Any]:
        started = perf_counter()
        vehicle_state = await self._vehicle_service.get_state(state["vehicle_id"])
        await self._step(state, "load_context", started, f"vehicle_version={vehicle_state.version}")
        return {"vehicle_state": vehicle_state, "step_sequence": state["step_sequence"] + 1}

    async def route_intent(self, state: AgentState) -> dict[str, Any]:
        started = perf_counter()
        result = self._router.route(state["input_text"])
        await self._step(
            state, "route_intent", started, f"route={result.route}; intent={result.intent}"
        )
        return {
            "route": result.route,
            "intent": result.intent,
            "planned_calls": result.calls,
            "reply_hint": result.reply_hint,
            "observed_speed_kph": result.observed_speed_kph,
            "step_sequence": state["step_sequence"] + 1,
        }

    async def model_plan(self, state: AgentState) -> dict[str, Any]:
        started = perf_counter()
        try:
            result = await self._model.plan(
                state["input_text"], state["vehicle_state"], self._registry.model_tool_catalog()
            )
            output = {
                "intent": result.plan.intent,
                "planned_calls": [call.model_dump() for call in result.plan.tool_calls],
                "reply_hint": result.plan.reply,
                "model": result.model,
                "llm_calls": state["llm_calls"] + 1,
                "token_in": state["token_in"] + result.input_tokens,
                "token_out": state["token_out"] + result.output_tokens,
                "cost_est_cny": state["cost_est_cny"] + result.cost_est_cny,
            }
            summary = f"model={result.model}; calls={len(result.plan.tool_calls)}"
        except ModelGatewayDisabled:
            output = {
                "planned_calls": [],
                "reply_hint": "该请求需要进一步理解，但当前未配置模型服务。",
            }
            summary = "model_disabled"
        except ModelGatewayError:
            output = {"planned_calls": [], "reply_hint": "模型服务暂时不可用，请稍后重试。"}
            summary = "model_unavailable"
        await self._step(state, "model_plan", started, summary)
        return {**output, "step_sequence": state["step_sequence"] + 1}

    async def validate_tools(self, state: AgentState) -> dict[str, Any]:
        started = perf_counter()
        commands = []
        rejected = 0
        for raw in state.get("planned_calls", []):
            try:
                commands.append(self._registry.validate(ToolCallPlan.model_validate(raw)))
            except (ValueError, TypeError):
                rejected += 1
        await self._step(
            state,
            "validate_tools",
            started,
            f"accepted={len(commands)}; rejected={rejected}",
        )
        return {"commands": commands, "step_sequence": state["step_sequence"] + 1}

    async def safety_gate(self, state: AgentState) -> dict[str, Any]:
        started = perf_counter()
        actions = [
            self._safety.authorize(
                command,
                state["vehicle_state"],
                observed_speed_kph=state.get("observed_speed_kph"),
            )
            for command in state.get("commands", [])
        ]
        blocked = sum(isinstance(action, SafetyDecision) for action in actions)
        await self._step(
            state,
            "safety_gate",
            started,
            f"approved={len(actions) - blocked}; blocked={blocked}",
        )
        return {"safety_actions": actions, "step_sequence": state["step_sequence"] + 1}

    async def execute_tools(self, state: AgentState) -> dict[str, Any]:
        started = perf_counter()
        outcomes: list[dict[str, Any]] = []
        current_state = state["vehicle_state"]
        for action in state.get("safety_actions", []):
            tool_started = perf_counter()
            if isinstance(action, SafetyDecision):
                command = state["commands"][len(outcomes)]
                latency = round((perf_counter() - tool_started) * 1000)
                outcome = {
                    "name": command.name,
                    "params": command.arguments,
                    "status": "BLOCKED",
                    "durationMs": latency,
                    "safetyReason": action.reason,
                    "safetyCode": action.code,
                }
                await self._trace.record_tool_call(
                    run_id=state["run_id"],
                    tool_name=command.name,
                    arguments=command.arguments,
                    result={"reason": action.reason},
                    latency_ms=latency,
                    status="blocked",
                    safety_decision="rejected",
                    safety_code=action.code,
                )
            else:
                assert isinstance(action, AuthorizedToolCall)
                try:
                    change = await self._executor.execute(
                        action,
                        vehicle_id=state["vehicle_id"],
                        expected_version=current_state.version,
                        request_id=state["request_id"],
                    )
                    current_state = change.state
                    status = "SUCCESS"
                    result_payload = {
                        "new_value": change.new_value,
                        "version": current_state.version,
                    }
                    safety_reason = None
                except Exception as exc:
                    status = "FAILED"
                    result_payload = {"error": type(exc).__name__}
                    safety_reason = None
                latency = round((perf_counter() - tool_started) * 1000)
                outcome = {
                    "name": action.command.name,
                    "params": action.command.arguments,
                    "status": status,
                    "durationMs": latency,
                    "safetyReason": safety_reason,
                }
                await self._trace.record_tool_call(
                    run_id=state["run_id"],
                    tool_name=action.command.name,
                    arguments=action.command.arguments,
                    result=result_payload,
                    latency_ms=latency,
                    status=status.lower(),
                    safety_decision="approved",
                    safety_code="APPROVED",
                )
            outcomes.append(outcome)

        await self._step(state, "execute_tools", started, f"tool_calls={len(outcomes)}")
        return {
            "outcomes": outcomes,
            "vehicle_state": current_state,
            "step_sequence": state["step_sequence"] + 1,
        }

    async def compose_response(self, state: AgentState) -> dict[str, Any]:
        started = perf_counter()
        outcomes = state.get("outcomes", [])
        blocked = [item for item in outcomes if item["status"] == "BLOCKED"]
        failed = [item for item in outcomes if item["status"] == "FAILED"]
        successful = [item for item in outcomes if item["status"] == "SUCCESS"]
        vehicle = state["vehicle_state"]
        if blocked:
            response = f"为保证行车安全，本次操作未执行：{blocked[0]['safetyReason']}"
        elif failed:
            response = "车辆操作未能完成，请稍后重试。"
        elif state.get("route") == "vehicle_info":
            response = f"当前电量 {vehicle.battery_soc:g}%，预计续航 {vehicle.range_km:g} km。"
        elif successful and state.get("reply_hint") == "driver_warm":
            response = "已将主驾温度调到 24℃，并开启 1 挡座椅加热。"
        elif successful and state.get("reply_hint") == "passenger_warm":
            response = "已按前排乘客理解，将副驾温度调到 25℃，并开启 1 挡座椅加热。"
        elif successful:
            response = f"已完成 {len(successful)} 项车辆设置。"
        else:
            response = state.get("reply_hint") or "我暂时无法确认这项请求，请换一种更明确的说法。"
        await self._step(state, "compose_response", started, f"response_length={len(response)}")
        return {"response_text": response, "step_sequence": state["step_sequence"] + 1}

    async def _step(
        self, state: AgentState, node_name: str, started: float, output_summary: str
    ) -> None:
        await self._trace.record_step(
            run_id=state["run_id"],
            sequence=state["step_sequence"] + 1,
            node_name=node_name,
            latency_ms=round((perf_counter() - started) * 1000),
            status="success",
            input_summary=None,
            output_summary=output_summary[:500],
        )
