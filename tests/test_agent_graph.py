import pytest

from apps.api.agents.service import CockpitAgentService
from apps.api.core.config import Settings
from apps.api.domain.vehicle.service import VehicleService
from apps.api.models.base import ModelPlanResult
from apps.api.models.gateway import ModelGateway
from apps.api.tools.schemas import ModelPlan, ToolCallPlan
from tests.fakes import DEMO_VEHICLE_ID, InMemoryAgentTraceStore, InMemoryVehicleHAL


def _service():
    settings = Settings(app_env="test", llm_api_key=None, llm_base_url="", llm_model="")
    hal = InMemoryVehicleHAL()
    traces = InMemoryAgentTraceStore()
    service = CockpitAgentService(
        vehicle_service=VehicleService(hal),
        trace_store=traces,
        model_gateway=ModelGateway(settings),
    )
    return service, hal, traces


@pytest.mark.asyncio
async def test_driver_cold_executes_two_tools_without_llm() -> None:
    service, hal, traces = _service()
    result = await service.run(
        request_id="cold-driver",
        conversation_id=None,
        vehicle_id=DEMO_VEHICLE_ID,
        text="我有点冷",
    )

    assert result.llm_calls == 0
    assert result.blocked is False
    assert hal.state.climate["driver"] == 24
    assert hal.state.seat_heat["driver"] == 1
    assert len(traces.tool_calls) == 2
    assert traces.completed and traces.completed["status"] == "success"


@pytest.mark.asyncio
async def test_high_speed_door_request_is_blocked_and_audited() -> None:
    service, hal, traces = _service()
    result = await service.run(
        request_id="unsafe-door",
        conversation_id=None,
        vehicle_id=DEMO_VEHICLE_ID,
        text="120km/h开门",
    )

    assert result.blocked is True
    assert hal.state.door_state["driver"] == "CLOSED"
    assert traces.tool_calls[0]["status"] == "blocked"
    assert traces.tool_calls[0]["safety_code"] == "DOOR_OPEN_WHILE_MOVING"


@pytest.mark.asyncio
async def test_ambiguous_request_degrades_safely_without_model() -> None:
    service, _, traces = _service()
    result = await service.run(
        request_id="ambiguous",
        conversation_id=None,
        vehicle_id=DEMO_VEHICLE_ID,
        text="帮我弄舒服一点",
    )

    assert result.llm_calls == 0
    assert result.outcomes == []
    assert "未配置模型" in result.response_text
    assert traces.completed and traces.completed["status"] == "success"


class FakePlanner:
    async def plan(self, text, state, tool_catalog):
        return ModelPlanResult(
            plan=ModelPlan(
                intent="cockpit_control",
                reply="打开近光灯",
                tool_calls=[ToolCallPlan(name="set_light", arguments={"state": "LOW_BEAM"})],
            ),
            provider="fake",
            model="fake-planner",
            input_tokens=10,
            output_tokens=5,
            latency_ms=1,
            cost_est_cny=0.001,
        )


@pytest.mark.asyncio
async def test_ambiguous_request_uses_one_model_call_then_safety_gate() -> None:
    settings = Settings(app_env="test")
    hal = InMemoryVehicleHAL()
    traces = InMemoryAgentTraceStore()
    service = CockpitAgentService(
        vehicle_service=VehicleService(hal),
        trace_store=traces,
        model_gateway=ModelGateway(settings, planner=FakePlanner()),
    )

    result = await service.run(
        request_id="model-once",
        conversation_id=None,
        vehicle_id=DEMO_VEHICLE_ID,
        text="让前面亮一点",
    )

    assert result.llm_calls == 1
    assert result.model == "fake-planner"
    assert hal.state.light_state == "LOW_BEAM"
    assert any(step["node_name"] == "safety_gate" for step in traces.steps)
