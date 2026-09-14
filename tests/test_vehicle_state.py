from fastapi.testclient import TestClient

from apps.api.api.dependencies import get_vehicle_service
from apps.api.domain.vehicle.exceptions import VehicleStorageError


class UnavailableVehicleService:
    async def get_state(self, _) -> None:  # type: ignore[no-untyped-def]
        raise VehicleStorageError("unavailable")


def test_vehicle_state_uses_live_contract(client: TestClient) -> None:
    response = client.get("/api/v1/vehicle/state", headers={"X-Request-ID": "vehicle-state-test"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["request_id"] == "vehicle-state-test"
    assert payload["source"] == "live"
    assert payload["state"]["vehicle_id"] == "00000000-0000-0000-0000-000000000001"
    assert payload["state"]["gear"] == "P"
    assert payload["state"]["climate"]["driver_temp_c"] == 22
    assert payload["state"]["version"] == 0


def test_control_updates_state_and_increments_version(client: TestClient) -> None:
    response = client.post(
        "/api/v1/vehicle/control",
        headers={"X-Request-ID": "temperature-change"},
        json={
            "property": "DRIVER_TEMP",
            "zone": "driver",
            "value": 24,
            "expected_version": 0,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["request_id"] == "temperature-change"
    assert payload["change"] == {
        "property": "DRIVER_TEMP",
        "zone": "driver",
        "old_value": 22,
        "new_value": 24.0,
    }
    assert payload["state"]["climate"]["driver_temp_c"] == 24
    assert payload["state"]["version"] == 1


def test_invalid_temperature_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/v1/vehicle/control",
        json={"property": "DRIVER_TEMP", "value": 31, "expected_version": 0},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_PROPERTY_VALUE"


def test_read_only_property_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/v1/vehicle/control",
        json={"property": "VEHICLE_SPEED", "value": 10, "expected_version": 0},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "READ_ONLY_PROPERTY"


def test_stale_version_returns_conflict(client: TestClient) -> None:
    response = client.post(
        "/api/v1/vehicle/control",
        json={"property": "LIGHT_STATE", "value": "LOW_BEAM", "expected_version": 9},
    )

    assert response.status_code == 409
    assert response.json()["error"] == {
        "code": "VEHICLE_VERSION_CONFLICT",
        "message": "Vehicle state was updated by another request",
        "details": {"expected_version": 9, "current_version": 0},
    }


def test_unversioned_vehicle_route_is_not_exposed(client: TestClient) -> None:
    assert client.get("/vehicle/state").status_code == 404


def test_database_failure_returns_service_unavailable(client: TestClient) -> None:
    client.app.dependency_overrides[get_vehicle_service] = UnavailableVehicleService
    response = client.get("/api/v1/vehicle/state")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "VEHICLE_STORAGE_UNAVAILABLE"
