from typing import Any
from uuid import UUID

from apps.api.domain.vehicle.entities import (
    VehiclePropertyValue,
    VehicleStateChange,
    VehicleStateData,
)
from apps.api.domain.vehicle.exceptions import VehicleNotFoundError
from apps.api.domain.vehicle.hal import VehicleHAL
from apps.api.domain.vehicle.properties import (
    VehicleProperty,
    VehicleZone,
    normalize_property_value,
)


class VehicleService:
    def __init__(self, hal: VehicleHAL) -> None:
        self._hal = hal

    async def get_state(self, vehicle_id: UUID) -> VehicleStateData:
        state = await self._hal.get_state(vehicle_id)
        if state is None:
            raise VehicleNotFoundError(vehicle_id)
        return state

    async def get_property(
        self,
        vehicle_id: UUID,
        property_name: VehicleProperty,
        zone: VehicleZone | None = None,
    ) -> VehiclePropertyValue:
        result = await self._hal.get_property(
            vehicle_id, property_name, zone.value if zone else None
        )
        if result is None:
            raise VehicleNotFoundError(vehicle_id)
        return result

    async def set_property(
        self,
        vehicle_id: UUID,
        property_name: VehicleProperty,
        zone: VehicleZone | None,
        value: Any,
        *,
        expected_version: int,
        request_id: str,
    ) -> VehicleStateChange:
        normalized_zone, normalized_value = normalize_property_value(property_name, zone, value)
        return await self._hal.set_property(
            vehicle_id,
            property_name,
            normalized_zone,
            normalized_value,
            expected_version=expected_version,
            request_id=request_id,
        )
