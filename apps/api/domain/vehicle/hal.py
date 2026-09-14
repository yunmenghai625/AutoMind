from typing import Any, Protocol
from uuid import UUID

from apps.api.domain.vehicle.entities import (
    VehiclePropertyValue,
    VehicleStateChange,
    VehicleStateData,
)
from apps.api.domain.vehicle.properties import VehicleProperty


class VehicleHAL(Protocol):
    async def get_state(self, vehicle_id: UUID) -> VehicleStateData | None: ...

    async def get_property(
        self, vehicle_id: UUID, property_name: VehicleProperty, zone: str | None
    ) -> VehiclePropertyValue | None: ...

    async def set_property(
        self,
        vehicle_id: UUID,
        property_name: VehicleProperty,
        zone: str | None,
        value: Any,
        *,
        expected_version: int,
        request_id: str,
    ) -> VehicleStateChange: ...
