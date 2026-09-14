import pytest
from fastapi.testclient import TestClient

from apps.api.agents.service import CockpitAgentService
from apps.api.api.dependencies import get_cockpit_agent_service, get_vehicle_service
from apps.api.core.config import Settings
from apps.api.domain.vehicle.service import VehicleService
from apps.api.main import create_app
from apps.api.models.gateway import ModelGateway
from tests.fakes import InMemoryAgentTraceStore, InMemoryVehicleHAL


@pytest.fixture
def client() -> TestClient:
    settings = Settings(
        app_env="test",
        database_healthcheck_enabled=False,
        cors_origins="http://localhost:3000",
        usage_quota_enabled=False,
        rate_limit_enabled=False,
        operational_metrics_persistence_enabled=False,
    )
    app = create_app(settings)
    vehicle_service = VehicleService(InMemoryVehicleHAL())
    trace_store = InMemoryAgentTraceStore()
    agent_service = CockpitAgentService(
        vehicle_service=vehicle_service,
        trace_store=trace_store,
        model_gateway=ModelGateway(settings),
    )
    app.dependency_overrides[get_vehicle_service] = lambda: vehicle_service
    app.dependency_overrides[get_cockpit_agent_service] = lambda: agent_service
    with TestClient(app) as test_client:
        yield test_client
