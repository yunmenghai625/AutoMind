from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.domain.vehicle.entities import (
    VehiclePropertyValue,
    VehicleStateChange,
    VehicleStateData,
)
from apps.api.domain.vehicle.exceptions import (
    VehicleNotFoundError,
    VehicleStorageError,
    VehicleVersionConflictError,
)
from apps.api.domain.vehicle.properties import VehicleProperty, apply_property, read_property
from apps.api.infrastructure.models import VehicleStateAuditRecord, VehicleStateRecord


class PostgresVehicleHAL:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_state(self, vehicle_id: UUID) -> VehicleStateData | None:
        try:
            async with self._session.begin():
                record = await self._get_record(vehicle_id)
        except SQLAlchemyError as exc:
            raise VehicleStorageError("Vehicle storage is unavailable") from exc
        return _to_entity(record) if record else None

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
        try:
            return await self._set_property_transaction(
                vehicle_id,
                property_name,
                zone,
                value,
                expected_version=expected_version,
                request_id=request_id,
            )
        except SQLAlchemyError as exc:
            raise VehicleStorageError("Vehicle storage is unavailable") from exc

    async def _set_property_transaction(
        self,
        vehicle_id: UUID,
        property_name: VehicleProperty,
        zone: str | None,
        value: Any,
        *,
        expected_version: int,
        request_id: str,
    ) -> VehicleStateChange:
        async with self._session.begin():
            record = await self._get_record(vehicle_id)
            if record is None:
                raise VehicleNotFoundError(vehicle_id)

            current_state = _to_entity(record)
            if current_state.version != expected_version:
                raise VehicleVersionConflictError(expected_version, current_state.version)

            old_value = read_property(current_state, property_name, zone)
            candidate_state = apply_property(current_state, property_name, zone, value)
            next_version = current_state.version + 1

            statement = (
                update(VehicleStateRecord)
                .where(
                    VehicleStateRecord.vehicle_id == vehicle_id,
                    VehicleStateRecord.version == current_state.version,
                )
                .values(
                    gear=candidate_state.gear,
                    climate_json=candidate_state.climate,
                    seat_heat_json=candidate_state.seat_heat,
                    window_position_json=candidate_state.window_position,
                    door_state_json=candidate_state.door_state,
                    light_state=candidate_state.light_state,
                    charge_status=candidate_state.charge_status,
                    version=next_version,
                )
                .returning(VehicleStateRecord)
            )
            result = await self._session.execute(statement)
            updated_record = result.scalar_one_or_none()
            if updated_record is None:
                actual_version = await self._current_version(vehicle_id)
                raise VehicleVersionConflictError(expected_version, actual_version)

            self._session.add(
                VehicleStateAuditRecord(
                    vehicle_id=vehicle_id,
                    request_id=request_id,
                    property_name=property_name.value,
                    zone=zone,
                    old_value_json=old_value,
                    new_value_json=value,
                    state_version=next_version,
                )
            )

        updated_state = _to_entity(updated_record)
        return VehicleStateChange(
            state=updated_state,
            property_name=property_name.value,
            zone=zone,
            old_value=old_value,
            new_value=value,
        )

    async def _get_record(self, vehicle_id: UUID) -> VehicleStateRecord | None:
        result = await self._session.execute(
            select(VehicleStateRecord).where(VehicleStateRecord.vehicle_id == vehicle_id)
        )
        return result.scalar_one_or_none()

    async def _current_version(self, vehicle_id: UUID) -> int:
        result = await self._session.execute(
            select(VehicleStateRecord.version).where(VehicleStateRecord.vehicle_id == vehicle_id)
        )
        version = result.scalar_one_or_none()
        if version is None:
            raise VehicleNotFoundError(vehicle_id)
        return version


def _to_entity(record: VehicleStateRecord) -> VehicleStateData:
    return VehicleStateData(
        vehicle_id=record.vehicle_id,
        speed_kph=record.speed_kph,
        gear=record.gear,
        battery_soc=record.battery_soc,
        range_km=record.range_km,
        climate={key: float(value) for key, value in record.climate_json.items()},
        seat_heat={key: int(value) for key, value in record.seat_heat_json.items()},
        window_position={key: float(value) for key, value in record.window_position_json.items()},
        door_state={key: str(value) for key, value in record.door_state_json.items()},
        light_state=record.light_state,
        charge_status=record.charge_status,
        version=record.version,
        updated_at=record.updated_at,
    )
