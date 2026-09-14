from dataclasses import replace
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from apps.api.domain.vehicle.entities import (
    VehiclePropertyValue,
    VehicleStateChange,
    VehicleStateData,
)
from apps.api.domain.vehicle.exceptions import (
    VehicleNotFoundError,
    VehicleVersionConflictError,
)
from apps.api.domain.vehicle.properties import VehicleProperty, apply_property, read_property

DEMO_VEHICLE_ID = UUID("00000000-0000-0000-0000-000000000001")


class InMemoryVehicleHAL:
    def __init__(self) -> None:
        self.state = VehicleStateData(
            vehicle_id=DEMO_VEHICLE_ID,
            speed_kph=0,
            gear="P",
            battery_soc=78,
            range_km=421,
            climate={"driver": 22, "passenger": 22},
            seat_heat={"driver": 0, "passenger": 0},
            window_position={"driver": 0, "passenger": 0},
            door_state={"driver": "CLOSED", "passenger": "CLOSED"},
            light_state="OFF",
            charge_status="IDLE",
            version=0,
            updated_at=datetime.now(UTC),
        )
        self.audit_request_ids: list[str] = []

    async def get_state(self, vehicle_id: UUID) -> VehicleStateData | None:
        return self.state if vehicle_id == self.state.vehicle_id else None

    async def get_property(
        self, vehicle_id: UUID, property_name: VehicleProperty, zone: str | None
    ) -> VehiclePropertyValue | None:
        state = await self.get_state(vehicle_id)
        if state is None:
            return None
        return VehiclePropertyValue(
            property_name=property_name.value,
            zone=zone,
            value=read_property(state, property_name, zone),
        )

    async def set_property(
        self,
        vehicle_id: UUID,
        property_name: VehicleProperty,
        zone: str | None,
        value: Any,
        *,
        expected_version: int,
        request_id: str,
    ) -> VehicleStateChange:
        if vehicle_id != self.state.vehicle_id:
            raise VehicleNotFoundError(vehicle_id)
        if expected_version != self.state.version:
            raise VehicleVersionConflictError(expected_version, self.state.version)

        old_value = read_property(self.state, property_name, zone)
        updated = apply_property(self.state, property_name, zone, value)
        self.state = replace(updated, version=updated.version + 1, updated_at=datetime.now(UTC))
        self.audit_request_ids.append(request_id)
        return VehicleStateChange(
            state=self.state,
            property_name=property_name.value,
            zone=zone,
            old_value=old_value,
            new_value=value,
        )


class InMemoryAgentTraceStore:
    def __init__(self) -> None:
        self.runs: list[dict[str, Any]] = []
        self.steps: list[dict[str, Any]] = []
        self.tool_calls: list[dict[str, Any]] = []
        self.completed: dict[str, Any] | None = None

    async def create_run(self, **values: Any) -> UUID:
        run_id = uuid4()
        self.runs.append({"id": run_id, **values})
        return run_id

    async def record_step(self, **values: Any) -> None:
        self.steps.append(values)

    async def record_tool_call(self, **values: Any) -> None:
        self.tool_calls.append(values)

    async def complete_run(self, **values: Any) -> None:
        self.completed = values
