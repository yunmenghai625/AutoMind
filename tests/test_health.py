from fastapi.testclient import TestClient

from apps.api.api.routes import health as health_route
from apps.api.schemas.health import DependencyHealth


def test_versioned_health_reports_dependencies(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["version"] == "1.0.0"
    assert payload["environment"] == "test"
    assert payload["dependencies"]["database"]["status"] == "disabled"
    assert response.headers["X-Request-ID"]


def test_root_health_alias_is_available(client: TestClient) -> None:
    assert client.get("/health").status_code == 200


def test_unknown_route_uses_unified_error_shape(client: TestClient) -> None:
    response = client.get("/does-not-exist", headers={"X-Request-ID": "test-request-1"})

    assert response.status_code == 404
    assert response.headers["X-Request-ID"] == "test-request-1"
    assert response.json() == {
        "error": {"code": "NOT_FOUND", "message": "Not Found", "details": None},
        "request_id": "test-request-1",
    }


def test_unavailable_database_degrades_health_without_crashing(
    client: TestClient, monkeypatch
) -> None:
    async def unavailable_database(_) -> DependencyHealth:  # type: ignore[no-untyped-def]
        return DependencyHealth(status="unavailable", detail="TimeoutError")

    monkeypatch.setattr(health_route, "check_database", unavailable_database)
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["dependencies"]["database"] == {
        "status": "unavailable",
        "detail": "TimeoutError",
    }
