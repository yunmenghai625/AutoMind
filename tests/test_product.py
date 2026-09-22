from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from apps.api.aigc.repository import UsageSubject
from apps.api.api.dependencies import (
    get_admin_identity,
    get_garage_service,
    get_usage_subject,
    get_vehicle_service,
)
from apps.api.auth.service import (
    AdminAuthenticationError,
    AuthenticationError,
    AuthIdentity,
    JwtAuthenticator,
    create_admin_session,
    hash_admin_password,
    verify_admin_password,
)
from apps.api.core.config import Settings
from apps.api.domain.vehicle.service import VehicleService
from apps.api.main import create_app
from apps.api.product.schemas import FeedbackRequest, GarageVehicleView, PreferenceValues
from apps.api.product.service import (
    ExternalVehicleDataService,
    UsageQuotaExceededError,
    UsageQuotaService,
    normalize_vin,
)
from apps.api.product.vehicle_data import VehicleDataProviderError
from tests.fakes import DEMO_VEHICLE_ID, InMemoryVehicleHAL


def test_jwt_authenticator_accepts_registered_and_guest_identities() -> None:
    user_id = uuid4()
    secret = "phase5-test-secret-with-at-least-32-bytes"
    authenticator = JwtAuthenticator(secret=secret, issuer="automind", audience="users")
    token = jwt.encode(
        {
            "sub": str(user_id),
            "email": "driver@example.com",
            "role": "authenticated",
            "iss": "automind",
            "aud": "users",
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        secret,
        algorithm="HS256",
    )

    assert authenticator.authenticate(None).kind == "guest"
    identity = authenticator.authenticate(f"Bearer {token}")
    assert identity.user_id == user_id
    assert identity.email == "driver@example.com"


def test_jwt_authenticator_rejects_expired_token() -> None:
    secret = "phase5-test-secret-with-at-least-32-bytes"
    authenticator = JwtAuthenticator(secret=secret, issuer="", audience="")
    token = jwt.encode(
        {"sub": str(uuid4()), "exp": datetime.now(UTC) - timedelta(seconds=1)},
        secret,
        algorithm="HS256",
    )
    with pytest.raises(AuthenticationError):
        authenticator.authenticate(f"Bearer {token}")


def test_admin_password_hash_and_session_are_verified() -> None:
    password_hash = hash_admin_password(
        "portfolio-admin-password",
        salt=b"automind-test-salt",
    )
    assert verify_admin_password("portfolio-admin-password", password_hash) is True
    assert verify_admin_password("incorrect-password", password_hash) is False

    token, expires_at, identity = create_admin_session(
        submitted_username="YunMengHai625",
        submitted_password="portfolio-admin-password",
        configured_username="yunmenghai625",
        configured_password_hash=password_hash,
        jwt_secret="phase8-admin-jwt-secret-at-least-32-characters",
        issuer="automind",
        audience="authenticated",
        lifetime_hours=8,
    )
    decoded = JwtAuthenticator(
        secret="phase8-admin-jwt-secret-at-least-32-characters",
        issuer="automind",
        audience="authenticated",
    ).authenticate(f"Bearer {token}")
    assert expires_at > datetime.now(UTC)
    assert identity.role == "admin"
    assert decoded.user_id == identity.user_id
    assert decoded.role == "admin"

    with pytest.raises(AdminAuthenticationError):
        create_admin_session(
            submitted_username="yunmenghai625",
            submitted_password="incorrect-password",
            configured_username="yunmenghai625",
            configured_password_hash=password_hash,
            jwt_secret="phase8-admin-jwt-secret-at-least-32-characters",
            issuer="automind",
            audience="authenticated",
            lifetime_hours=8,
        )


def test_admin_uses_only_the_demo_vehicle_context() -> None:
    admin_id = uuid4()
    admin = UsageSubject(
        kind="registered",
        key=f"user:{admin_id}",
        user_id=admin_id,
        role="admin",
    )
    regular = UsageSubject(
        kind="registered",
        key=f"user:{admin_id}",
        user_id=admin_id,
        role="authenticated",
    )

    assert admin.vehicle_user_id is None
    assert regular.vehicle_user_id == admin_id


def test_admin_can_open_garage_and_cockpit_without_accessing_user_vehicles() -> None:
    admin_id = uuid4()
    subject = UsageSubject(
        kind="registered",
        key=f"user:{admin_id}",
        user_id=admin_id,
        role="admin",
    )
    captured_user_ids: list[object] = []

    class AdminDemoGarage:
        async def primary(self, *, user_id, demo_vehicle_id):
            captured_user_ids.append(user_id)
            assert demo_vehicle_id == DEMO_VEHICLE_ID
            return GarageVehicleView(
                id=DEMO_VEHICLE_ID,
                make="AutoMind",
                model="Demo",
                year=2026,
                powertrain="BEV",
                mileageKm=0,
                vinMasked=None,
                batterySoc=78,
                updatedAt=datetime.now(UTC),
                name="AutoMind Demo",
                vin="Not provided",
                lastCheck="2026-09-22",
                batteryHealth=None,
                trim="BEV",
                color="Not specified",
            )

        async def resolve_vehicle_id(self, *, user_id, requested_vehicle_id, demo_vehicle_id):
            captured_user_ids.append(user_id)
            assert requested_vehicle_id is None
            return demo_vehicle_id

    settings = Settings(
        app_env="test",
        database_healthcheck_enabled=False,
        rate_limit_enabled=False,
        operational_metrics_persistence_enabled=False,
    )
    app = create_app(settings)
    vehicle_service = VehicleService(InMemoryVehicleHAL())
    app.dependency_overrides[get_usage_subject] = lambda: subject
    app.dependency_overrides[get_garage_service] = lambda: AdminDemoGarage()
    app.dependency_overrides[get_vehicle_service] = lambda: vehicle_service

    with TestClient(app) as test_client:
        garage = test_client.get("/api/v1/garage/vehicle")
        cockpit = test_client.get("/api/v1/vehicle/state")

    assert garage.status_code == 200
    assert cockpit.status_code == 200
    assert captured_user_ids == [None, None]


def test_admin_can_control_ai_runtime_and_public_metrics_are_protected() -> None:
    settings = Settings(
        app_env="test",
        database_healthcheck_enabled=False,
        rate_limit_enabled=False,
        operational_metrics_persistence_enabled=False,
    )
    app = create_app(settings)

    with TestClient(app) as anonymous_client:
        metrics = anonymous_client.get("/api/v1/aigc/metrics")
    assert metrics.status_code == 401

    admin_id = uuid4()
    app.dependency_overrides[get_admin_identity] = lambda: AuthIdentity(
        kind="registered",
        user_id=admin_id,
        role="admin",
    )
    with TestClient(app) as admin_client:
        stopped = admin_client.put("/api/v1/admin/ai-control", json={"enabled": False})
        state = admin_client.get("/api/v1/admin/ai-control")

    assert stopped.status_code == 200
    assert stopped.json()["enabled"] is False
    assert state.json()["runtimeEnabled"] is False


def test_admin_login_endpoint_issues_a_working_bearer_token() -> None:
    password_hash = hash_admin_password(
        "portfolio-admin-password",
        salt=b"automind-api-test",
    )
    settings = Settings(
        app_env="test",
        database_healthcheck_enabled=False,
        rate_limit_enabled=False,
        operational_metrics_persistence_enabled=False,
        jwt_secret="phase8-login-jwt-secret-at-least-32-characters",
        jwt_issuer="automind",
        jwt_audience="authenticated",
        admin_username="yunmenghai625",
        admin_password_hash=password_hash,
    )
    with TestClient(create_app(settings)) as test_client:
        response = test_client.post(
            "/api/v1/auth/admin/login",
            json={"username": "yunmenghai625", "password": "portfolio-admin-password"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["tokenType"] == "Bearer"
        assert payload["user"]["role"] == "admin"

        me = test_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {payload['accessToken']}"},
        )
        assert me.status_code == 200
        assert me.json()["role"] == "admin"

        rejected = test_client.post(
            "/api/v1/auth/admin/login",
            json={"username": "yunmenghai625", "password": "incorrect-password"},
        )
        assert rejected.status_code == 401


def test_structured_preferences_and_feedback_reject_invalid_values() -> None:
    with pytest.raises(ValidationError):
        PreferenceValues(preferredTemperature=31)
    with pytest.raises(ValidationError):
        FeedbackRequest(rating=1)
    with pytest.raises(ValidationError):
        FeedbackRequest(run_id=uuid4(), rating=0)


@pytest.mark.parametrize("vin", ["1HGCM82633A004352", " 1hgcm82633a004352 "])
def test_vin_is_normalized(vin: str) -> None:
    assert normalize_vin(vin) == "1HGCM82633A004352"


@pytest.mark.parametrize("vin", ["1HGCM82633A00435I", "too-short", "1HGCM82633A00435-"])
def test_invalid_vin_is_rejected(vin: str) -> None:
    with pytest.raises(ValueError):
        normalize_vin(vin)


class _MemoryExternalRepository:
    def __init__(self) -> None:
        self.record = None

    async def get_cache(self, _: str):
        return self.record

    async def save_cache(self, **values):
        self.record = SimpleNamespace(
            normalized_json=values["normalized"],
            source=values["source"],
            fetched_at=values["fetched_at"],
            expires_at=values["expires_at"],
        )
        return self.record


class _VinProvider:
    name = "test-provider"

    def __init__(self) -> None:
        self.calls = 0
        self.fail = False

    async def decode_vin(self, _: str, __: int | None):
        self.calls += 1
        if self.fail:
            raise VehicleDataProviderError("offline")
        return {
            "make": "AutoMind",
            "model": "X1",
            "model_year": 2026,
            "vehicle_type": "Passenger Car",
            "fuel_type": "Electric",
        }

    async def recalls(self, *, make: str, model: str, year: int):
        return []


@pytest.mark.asyncio
async def test_external_vin_data_uses_cache_and_degrades_to_stale_data() -> None:
    repository = _MemoryExternalRepository()
    provider = _VinProvider()
    service = ExternalVehicleDataService(
        repository=repository,
        garage=SimpleNamespace(),
        provider=provider,
        cache_ttl_hours=1,
        vin_secret="vin-secret",
    )

    first = await service.decode_vin("1HGCM82633A004352", 2026)
    cached = await service.decode_vin("1HGCM82633A004352", 2026)
    assert first.status == "success"
    assert cached.status == "cached"
    assert provider.calls == 1
    assert first.vin_masked == "*************4352"

    repository.record.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    provider.fail = True
    degraded = await service.decode_vin("1HGCM82633A004352", 2026)
    assert degraded.status == "degraded"
    assert degraded.cached is True
    assert degraded.make == "AutoMind"


class _QuotaRepository:
    def __init__(self) -> None:
        self.counts: dict[str, int] = {}

    async def reserve_text(self, subject: UsageSubject, limit: int) -> int | None:
        next_value = self.counts.get(subject.key, 0) + 1
        if next_value > limit:
            return None
        self.counts[subject.key] = next_value
        return next_value


@pytest.mark.asyncio
async def test_guest_and_registered_text_limits_are_independent() -> None:
    service = UsageQuotaService(_QuotaRepository(), enabled=True)
    guest = UsageSubject(key="guest:test", kind="guest", user_id=None)
    registered = UsageSubject(key=f"user:{uuid4()}", kind="registered", user_id=uuid4())

    assert await service.reserve_text(guest, 1) == 1
    with pytest.raises(UsageQuotaExceededError):
        await service.reserve_text(guest, 1)
    assert await service.reserve_text(registered, 2) == 1
    assert await service.reserve_text(registered, 2) == 2
