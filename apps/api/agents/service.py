from dataclasses import dataclass
from time import perf_counter
from typing import Any
from uuid import UUID

from apps.api.agents.graph import CockpitAgentGraph
from apps.api.agents.trace import AgentTraceStore
from apps.api.domain.vehicle.entities import VehicleStateData
from apps.api.domain.vehicle.service import VehicleService
from apps.api.models.gateway import ModelGateway


@dataclass(frozen=True, slots=True)
class AgentResult:
    run_id: UUID
    response_text: str
    vehicle_state: VehicleStateData
    outcomes: list[dict[str, Any]]
    latency_ms: int
    model: str | None
    llm_calls: int

    @property
    def blocked(self) -> bool:
        return any(outcome["status"] == "BLOCKED" for outcome in self.outcomes)


class CockpitAgentService:
    def __init__(
        self,
        *,
        vehicle_service: VehicleService,
        trace_store: AgentTraceStore,
        model_gateway: ModelGateway,
    ) -> None:
        self._trace = trace_store
        self._graph = CockpitAgentGraph(
            vehicle_service=vehicle_service,
            trace_store=trace_store,
            model_gateway=model_gateway,
        )

    async def run(
        self,
        *,
        request_id: str,
        conversation_id: UUID | None,
        vehicle_id: UUID,
        text: str,
    ) -> AgentResult:
        started = perf_counter()
        run_id = await self._trace.create_run(
            request_id=request_id,
            conversation_id=conversation_id,
            input_text=text,
            agent_name="CockpitAgent",
        )
        initial = {
            "request_id": request_id,
            "run_id": run_id,
            "vehicle_id": vehicle_id,
            "input_text": text,
            "step_sequence": 0,
            "llm_calls": 0,
            "token_in": 0,
            "token_out": 0,
            "cost_est_cny": 0.0,
            "outcomes": [],
        }
        try:
            final = await self._graph.compiled.ainvoke(initial, {"recursion_limit": 16})
        except Exception as exc:
            latency_ms = round((perf_counter() - started) * 1000)
            await self._trace.complete_run(
                run_id=run_id,
                latency_ms=latency_ms,
                status="failed",
                model=None,
                token_in=0,
                token_out=0,
                cost_est_cny=0,
                llm_calls=0,
                response_summary=None,
                error_code=type(exc).__name__,
            )
            raise

        latency_ms = round((perf_counter() - started) * 1000)
        outcomes = final.get("outcomes", [])
        if any(item["status"] == "FAILED" for item in outcomes):
            status = "failed"
        elif any(item["status"] == "BLOCKED" for item in outcomes):
            status = "blocked"
        else:
            status = "success"
        await self._trace.complete_run(
            run_id=run_id,
            latency_ms=latency_ms,
            status=status,
            model=final.get("model"),
            token_in=final.get("token_in", 0),
            token_out=final.get("token_out", 0),
            cost_est_cny=final.get("cost_est_cny", 0),
            llm_calls=final.get("llm_calls", 0),
            response_summary=final["response_text"][:500],
        )
        return AgentResult(
            run_id=run_id,
            response_text=final["response_text"],
            vehicle_state=final["vehicle_state"],
            outcomes=outcomes,
            latency_ms=latency_ms,
            model=final.get("model"),
            llm_calls=final.get("llm_calls", 0),
        )
