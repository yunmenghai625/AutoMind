from dataclasses import replace

import pytest

from apps.api.domain.safety.policy import (
    AuthorizedToolCall,
    SafetyDecision,
    SafetyPolicyEngine,
)
from apps.api.domain.vehicle.service import VehicleService
from apps.api.tools.registry import ToolExecutor, ToolRegistry
from apps.api.tools.schemas import ToolCallPlan
from tests.fakes import DEMO_VEHICLE_ID, InMemoryVehicleHAL


def _door_command():
    return ToolRegistry().validate(
        ToolCallPlan(name="set_door_state", arguments={"zone": "driver", "state": "OPEN"})
    )


@pytest.mark.asyncio
async def test_moving_vehicle_door_open_is_always_rejected() -> None:
    hal = InMemoryVehicleHAL()
    hal.state = replace(hal.state, speed_kph=1)
    decision = SafetyPolicyEngine().evaluate(_door_command(), hal.state)

    assert decision.approved is False
    assert decision.code == "DOOR_OPEN_WHILE_MOVING"


@pytest.mark.asyncio
async def test_stated_speed_blocks_even_when_digital_twin_is_stationary() -> None:
    hal = InMemoryVehicleHAL()
    decision = SafetyPolicyEngine().evaluate(_door_command(), hal.state, observed_speed_kph=120)

    assert decision.approved is False
    assert decision.code == "DOOR_OPEN_WHILE_MOVING"


@pytest.mark.asyncio
async def test_executor_rejects_forged_safety_permit() -> None:
    hal = InMemoryVehicleHAL()
    executor = ToolExecutor(VehicleService(hal))
    forged = AuthorizedToolCall(
        _door_command(), SafetyDecision(True, "APPROVED", "forged"), object()
    )

    with pytest.raises(PermissionError):
        await executor.execute(
            forged,
            vehicle_id=DEMO_VEHICLE_ID,
            expected_version=0,
            request_id="forged",
        )
    assert hal.state.door_state["driver"] == "CLOSED"
