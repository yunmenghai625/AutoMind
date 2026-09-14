from dataclasses import replace
from enum import StrEnum
from typing import Any

from apps.api.domain.vehicle.entities import VehicleStateData
from apps.api.domain.vehicle.exceptions import VehicleValidationError


class VehicleProperty(StrEnum):
    VEHICLE_SPEED = "VEHICLE_SPEED"
    GEAR = "GEAR"
    BATTERY_SOC = "BATTERY_SOC"
    RANGE_KM = "RANGE_KM"
    DRIVER_TEMP = "DRIVER_TEMP"
    PASSENGER_TEMP = "PASSENGER_TEMP"
    SEAT_HEAT = "SEAT_HEAT"
    WINDOW_POSITION = "WINDOW_POSITION"
    DOOR_STATE = "DOOR_STATE"
    LIGHT_STATE = "LIGHT_STATE"
    CHARGE_STATUS = "CHARGE_STATUS"


class VehicleZone(StrEnum):
    GLOBAL = "global"
    DRIVER = "driver"
    PASSENGER = "passenger"


READ_ONLY_PROPERTIES = {
    VehicleProperty.VEHICLE_SPEED,
    VehicleProperty.BATTERY_SOC,
    VehicleProperty.RANGE_KM,
}
ZONED_PROPERTIES = {
    VehicleProperty.SEAT_HEAT,
    VehicleProperty.WINDOW_POSITION,
    VehicleProperty.DOOR_STATE,
}


def _require_number(value: Any, *, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise VehicleValidationError("INVALID_PROPERTY_VALUE", "Value must be a number")
    normalized = float(value)
    if not minimum <= normalized <= maximum:
        raise VehicleValidationError(
            "INVALID_PROPERTY_VALUE", f"Value must be between {minimum:g} and {maximum:g}"
        )
    return normalized


def _require_integer(value: Any, *, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise VehicleValidationError("INVALID_PROPERTY_VALUE", "Value must be an integer")
    if not minimum <= value <= maximum:
        raise VehicleValidationError(
            "INVALID_PROPERTY_VALUE", f"Value must be between {minimum} and {maximum}"
        )
    return value


def _require_choice(value: Any, choices: set[str]) -> str:
    if not isinstance(value, str) or value.upper() not in choices:
        allowed = ", ".join(sorted(choices))
        raise VehicleValidationError("INVALID_PROPERTY_VALUE", f"Value must be one of: {allowed}")
    return value.upper()


def normalize_property_value(
    property_name: VehicleProperty,
    zone: VehicleZone | None,
    value: Any,
) -> tuple[str | None, Any]:
    if property_name in READ_ONLY_PROPERTIES:
        raise VehicleValidationError("READ_ONLY_PROPERTY", f"{property_name.value} is read-only")

    if property_name == VehicleProperty.DRIVER_TEMP:
        if zone not in {None, VehicleZone.DRIVER}:
            raise VehicleValidationError("INVALID_ZONE", "DRIVER_TEMP only supports driver zone")
        return VehicleZone.DRIVER.value, _require_number(value, minimum=16, maximum=30)

    if property_name == VehicleProperty.PASSENGER_TEMP:
        if zone not in {None, VehicleZone.PASSENGER}:
            raise VehicleValidationError(
                "INVALID_ZONE", "PASSENGER_TEMP only supports passenger zone"
            )
        return VehicleZone.PASSENGER.value, _require_number(value, minimum=16, maximum=30)

    if property_name in ZONED_PROPERTIES:
        if zone not in {VehicleZone.DRIVER, VehicleZone.PASSENGER}:
            raise VehicleValidationError(
                "INVALID_ZONE", f"{property_name.value} requires driver or passenger zone"
            )
        normalized_zone = zone.value
        if property_name == VehicleProperty.SEAT_HEAT:
            return normalized_zone, _require_integer(value, minimum=0, maximum=3)
        if property_name == VehicleProperty.WINDOW_POSITION:
            return normalized_zone, _require_number(value, minimum=0, maximum=100)
        return normalized_zone, _require_choice(value, {"OPEN", "CLOSED"})

    if zone not in {None, VehicleZone.GLOBAL}:
        raise VehicleValidationError(
            "INVALID_ZONE", f"{property_name.value} only supports global zone"
        )

    if property_name == VehicleProperty.GEAR:
        return VehicleZone.GLOBAL.value, _require_choice(value, {"P", "R", "N", "D"})
    if property_name == VehicleProperty.LIGHT_STATE:
        return VehicleZone.GLOBAL.value, _require_choice(
            value, {"OFF", "PARKING", "LOW_BEAM", "HIGH_BEAM"}
        )
    if property_name == VehicleProperty.CHARGE_STATUS:
        return VehicleZone.GLOBAL.value, _require_choice(value, {"IDLE", "CHARGING"})

    raise VehicleValidationError("UNSUPPORTED_PROPERTY", "Vehicle property is not supported")


def read_property(state: VehicleStateData, property_name: VehicleProperty, zone: str | None) -> Any:
    if property_name == VehicleProperty.VEHICLE_SPEED:
        return state.speed_kph
    if property_name == VehicleProperty.GEAR:
        return state.gear
    if property_name == VehicleProperty.BATTERY_SOC:
        return state.battery_soc
    if property_name == VehicleProperty.RANGE_KM:
        return state.range_km
    if property_name == VehicleProperty.DRIVER_TEMP:
        return state.climate[VehicleZone.DRIVER.value]
    if property_name == VehicleProperty.PASSENGER_TEMP:
        return state.climate[VehicleZone.PASSENGER.value]
    if property_name == VehicleProperty.SEAT_HEAT:
        return state.seat_heat[_required_zone(zone)]
    if property_name == VehicleProperty.WINDOW_POSITION:
        return state.window_position[_required_zone(zone)]
    if property_name == VehicleProperty.DOOR_STATE:
        return state.door_state[_required_zone(zone)]
    if property_name == VehicleProperty.LIGHT_STATE:
        return state.light_state
    if property_name == VehicleProperty.CHARGE_STATUS:
        return state.charge_status
    raise VehicleValidationError("UNSUPPORTED_PROPERTY", "Vehicle property is not supported")


def apply_property(
    state: VehicleStateData,
    property_name: VehicleProperty,
    zone: str | None,
    value: Any,
) -> VehicleStateData:
    if property_name == VehicleProperty.DRIVER_TEMP:
        climate = {**state.climate, VehicleZone.DRIVER.value: value}
        return replace(state, climate=climate)
    if property_name == VehicleProperty.PASSENGER_TEMP:
        climate = {**state.climate, VehicleZone.PASSENGER.value: value}
        return replace(state, climate=climate)
    if property_name == VehicleProperty.SEAT_HEAT:
        seat_heat = {**state.seat_heat, _required_zone(zone): value}
        return replace(state, seat_heat=seat_heat)
    if property_name == VehicleProperty.WINDOW_POSITION:
        window_position = {**state.window_position, _required_zone(zone): value}
        return replace(state, window_position=window_position)
    if property_name == VehicleProperty.DOOR_STATE:
        door_state = {**state.door_state, _required_zone(zone): value}
        return replace(state, door_state=door_state)
    if property_name == VehicleProperty.GEAR:
        return replace(state, gear=value)
    if property_name == VehicleProperty.LIGHT_STATE:
        return replace(state, light_state=value)
    if property_name == VehicleProperty.CHARGE_STATUS:
        return replace(state, charge_status=value)
    raise VehicleValidationError("READ_ONLY_PROPERTY", f"{property_name.value} cannot be changed")


def _required_zone(zone: str | None) -> str:
    if zone not in {VehicleZone.DRIVER.value, VehicleZone.PASSENGER.value}:
        raise VehicleValidationError("INVALID_ZONE", "A supported vehicle zone is required")
    return zone
