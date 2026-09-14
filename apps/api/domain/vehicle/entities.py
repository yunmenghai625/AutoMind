from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class VehicleStateData:
    vehicle_id: UUID
    speed_kph: float
    gear: str
    battery_soc: float
    range_km: float
    climate: dict[str, float]
    seat_heat: dict[str, int]
    window_position: dict[str, float]
    door_state: dict[str, str]
    light_state: str
    charge_status: str
    version: int
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class VehiclePropertyValue:
    property_name: str
    zone: str | None
    value: Any


@dataclass(frozen=True, slots=True)
class VehicleStateChange:
    state: VehicleStateData
    property_name: str
    zone: str | None
    old_value: Any
    new_value: Any
