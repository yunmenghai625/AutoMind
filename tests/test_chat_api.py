from fastapi.testclient import TestClient

from apps.api.agents.service import CockpitAgentService
from apps.api.api.dependencies import get_cockpit_agent_service, get_vehicle_service
from apps.api.core.config import Settings
from apps.api.domain.vehicle.service import VehicleService
from apps.api.main import create_app
from apps.api.models.gateway import ModelGateway
from tests.fakes import InMemoryAgentTraceStore, InMemoryVehicleHAL


def test_chat_response_matches_frontend_contract(client) -> None:
    response = client.post("/api/v1/chat", json={"message": "我妈有点冷"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["messages"][0]["role"] == "assistant"
    assert payload["messages"][0]["tools"][0]["status"] == "SUCCESS"
    assert payload["messages"][0]["meta"]["llmCalls"] == 0
    assert payload["vehicle"]["passengerTemperature"] == 25
    assert payload["vehicle"]["passengerSeatHeat"] == 1


def test_unsafe_chat_is_safety_warning(client) -> None:
    response = client.post("/api/v1/chat", json={"message": "120km/h开门"})

    assert response.status_code == 200
    message = response.json()["messages"][0]
    assert message["kind"] == "safety_warning"
    assert message["meta"]["blocked"] is True
    assert message["tools"][0]["status"] == "BLOCKED"


def test_chat_stream_emits_sse_events(client) -> None:
    response = client.get("/api/v1/chat/stream", params={"message": "电量还有多少"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: started" in response.text
    assert "event: message" in response.text
    assert "event: vehicle" in response.text
    assert "event: done" in response.text


def test_vehicle_snapshot_maps_headlight_to_frontend_enum(client) -> None:
    response = client.post("/api/v1/chat", json={"message": "打开近光灯"})

    assert response.status_code == 200
    assert response.json()["vehicle"]["headlight"] == "ON"


def test_ai_requests_have_a_dedicated_per_caller_rate_limit() -> None:
    settings = Settings(
        app_env="test",
        database_healthcheck_enabled=False,
        usage_quota_enabled=False,
        rate_limit_enabled=False,
        ai_rate_limit_per_minute=1,
        operational_metrics_persistence_enabled=False,
    )
    app = create_app(settings)
    vehicle_service = VehicleService(InMemoryVehicleHAL())
    agent_service = CockpitAgentService(
        vehicle_service=vehicle_service,
        trace_store=InMemoryAgentTraceStore(),
        model_gateway=ModelGateway(settings),
    )
    app.dependency_overrides[get_vehicle_service] = lambda: vehicle_service
    app.dependency_overrides[get_cockpit_agent_service] = lambda: agent_service

    with TestClient(app) as test_client:
        first = test_client.post("/api/v1/chat", json={"message": "电量还有多少"})
        second = test_client.post("/api/v1/chat", json={"message": "续航还有多少"})

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "AI_RATE_LIMIT_EXCEEDED"
