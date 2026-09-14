import pytest

from apps.api.domain.vehicle.exceptions import VehicleValidationError
from apps.api.domain.vehicle.properties import (
    VehicleProperty,
    VehicleZone,
    normalize_property_value,
)


@pytest.mark.parametrize(
    ("property_name", "zone", "value", "expected"),
    [
        (VehicleProperty.DRIVER_TEMP, None, 16, ("driver", 16.0)),
        (VehicleProperty.PASSENGER_TEMP, VehicleZone.PASSENGER, 30, ("passenger", 30.0)),
        (VehicleProperty.SEAT_HEAT, VehicleZone.DRIVER, 3, ("driver", 3)),
        (VehicleProperty.WINDOW_POSITION, VehicleZone.PASSENGER, 55, ("passenger", 55.0)),
        (VehicleProperty.DOOR_STATE, VehicleZone.DRIVER, "open", ("driver", "OPEN")),
        (VehicleProperty.GEAR, None, "d", ("global", "D")),
        (VehicleProperty.LIGHT_STATE, None, "low_beam", ("global", "LOW_BEAM")),
        (VehicleProperty.CHARGE_STATUS, None, "charging", ("global", "CHARGING")),
    ],
)
def test_vehicle_property_normalization(
    property_name: VehicleProperty,
    zone: VehicleZone | None,
    value: object,
    expected: tuple[str, object],
) -> None:
    assert normalize_property_value(property_name, zone, value) == expected


@pytest.mark.parametrize(
    ("property_name", "zone", "value", "code"),
    [
        (VehicleProperty.DRIVER_TEMP, None, 15, "INVALID_PROPERTY_VALUE"),
        (VehicleProperty.SEAT_HEAT, None, 1, "INVALID_ZONE"),
        (VehicleProperty.SEAT_HEAT, VehicleZone.DRIVER, True, "INVALID_PROPERTY_VALUE"),
        (VehicleProperty.WINDOW_POSITION, VehicleZone.DRIVER, 101, "INVALID_PROPERTY_VALUE"),
        (VehicleProperty.BATTERY_SOC, None, 50, "READ_ONLY_PROPERTY"),
    ],
)
def test_invalid_vehicle_property_values(
    property_name: VehicleProperty,
    zone: VehicleZone | None,
    value: object,
    code: str,
) -> None:
    with pytest.raises(VehicleValidationError) as exc_info:
        normalize_property_value(property_name, zone, value)
    assert exc_info.value.code == code
