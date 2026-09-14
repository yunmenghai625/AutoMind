from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from apps.api.domain.vehicle.properties import VehicleProperty, VehicleZone


class ClimateState(BaseModel):
    driver_temp_c: float = Field(ge=16, le=30)
    passenger_temp_c: float = Field(ge=16, le=30)


class ZonedSeatHeatState(BaseModel):
    driver: int = Field(ge=0, le=3)
    passenger: int = Field(ge=0, le=3)


class ZonedPercentageState(BaseModel):
    driver: float = Field(ge=0, le=100)
    passenger: float = Field(ge=0, le=100)


class ZonedDoorState(BaseModel):
    driver: Literal["OPEN", "CLOSED"]
    passenger: Literal["OPEN", "CLOSED"]


class VehicleState(BaseModel):
    vehicle_id: UUID
    speed_kph: float = Field(ge=0)
    gear: Literal["P", "R", "N", "D"]
    battery_soc: float = Field(ge=0, le=100)
    range_km: float = Field(ge=0)
    climate: ClimateState
    seat_heat: ZonedSeatHeatState
    window_position: ZonedPercentageState
    door_state: ZonedDoorState
    light_state: Literal["OFF", "PARKING", "LOW_BEAM", "HIGH_BEAM"]
    charge_status: Literal["IDLE", "CHARGING"]
    version: int = Field(ge=0)
    updated_at: datetime


class VehicleStateResponse(BaseModel):
    request_id: str
    source: Literal["live"]
    state: VehicleState


class VehicleControlRequest(BaseModel):
    vehicle_id: UUID | None = None
    property: VehicleProperty
    zone: VehicleZone | None = None
    value: bool | int | float | str
    expected_version: int = Field(ge=0)


class VehicleStateChange(BaseModel):
    property: VehicleProperty
    zone: VehicleZone | None
    old_value: Any
    new_value: Any


class VehicleControlResponse(BaseModel):
    request_id: str
    source: Literal["live"]
    change: VehicleStateChange
    state: VehicleState
