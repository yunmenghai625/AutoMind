from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest
from pydantic import ValidationError

from apps.api.aigc.repository import UsageSubject
from apps.api.auth.service import AuthenticationError, JwtAuthenticator
from apps.api.product.schemas import FeedbackRequest, PreferenceValues
from apps.api.product.service import (
    ExternalVehicleDataService,
    UsageQuotaExceededError,
    UsageQuotaService,
    normalize_vin,
)
from apps.api.product.vehicle_data import VehicleDataProviderError


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
