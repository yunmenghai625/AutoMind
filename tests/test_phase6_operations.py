import asyncio
import json
import logging

import pytest
from fastapi.testclient import TestClient

from apps.api.core.config import Settings
from apps.api.core.logging import JsonFormatter
from apps.api.core.rate_limit import RedisRateLimiter
from apps.api.core.resilience import CircuitBreaker, CircuitOpenError
from apps.api.main import create_app
from apps.api.models.gateway import ModelGateway
from apps.api.operations.service import BudgetGuard


class CostRepositoryStub:
    def __init__(self, spent: float) -> None:
        self.spent = spent

    async def daily_cost(self) -> float:
        return self.spent


@pytest.mark.asyncio
async def test_memory_rate_limiter_enforces_fixed_window() -> None:
    limiter = RedisRateLimiter(url="", limit=2, timeout_seconds=0.1)

    assert (await limiter.allow("guest-a")).allowed is True
    second = await limiter.allow("guest-a")
    rejected = await limiter.allow("guest-a")

    assert second.remaining == 0
    assert rejected.allowed is False
    assert rejected.retry_after_seconds > 0


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_provider_failures() -> None:
    breaker = CircuitBreaker(failure_threshold=2, recovery_seconds=30)

    async def fail() -> None:
        raise TimeoutError("provider unavailable")

    with pytest.raises(TimeoutError):
        await breaker.call(fail)
    with pytest.raises(TimeoutError):
        await breaker.call(fail)

    assert breaker.state == "open"
    with pytest.raises(CircuitOpenError):
        await breaker.call(fail)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("spent", "expected"),
    [(7.99, "normal"), (8.0, "economy"), (10.0, "exhausted")],
)
async def test_budget_guard_switches_operating_mode(spent: float, expected: str) -> None:
    guard = BudgetGuard(
        CostRepositoryStub(spent),  # type: ignore[arg-type]
        daily_limit=10,
        economy_ratio=0.8,
    )

    state = await guard.current()

    assert state.state == expected
    assert state.spent_cny == spent


def test_economy_mode_disables_optional_chat_planner() -> None:
    settings = Settings()

    gateway = ModelGateway(settings, planner=object(), economy_mode=True)  # type: ignore[arg-type]

    assert gateway.enabled is False


def test_json_logging_redacts_credentials_tokens_and_vin() -> None:
    record = logging.LogRecord(
        "automind.test",
        logging.INFO,
        __file__,
        1,
        "authorization=Bearer top-secret-token vin=1HGCM82633A004352",
        (),
        None,
    )
    record.api_key = "provider-key"
    record.payload = {"refresh_token": "refresh-secret", "safe": "visible"}

    payload = json.loads(JsonFormatter().format(record))
    serialized = json.dumps(payload)

    assert "top-secret-token" not in serialized
    assert "1HGCM82633A004352" not in serialized
    assert "provider-key" not in serialized
    assert "refresh-secret" not in serialized
    assert payload["payload"]["safe"] == "visible"


def test_global_timeout_keeps_trace_and_security_headers() -> None:
    app = create_app(
        Settings(
            app_env="test",
            database_healthcheck_enabled=False,
            request_timeout_seconds=0.01,
            rate_limit_enabled=False,
            operational_metrics_persistence_enabled=False,
        )
    )

    @app.get("/slow-phase6")
    async def slow_phase6() -> dict[str, bool]:
        await asyncio.sleep(0.1)
        return {"ok": True}

    with TestClient(app) as client:
        response = client.get("/slow-phase6", headers={"X-Request-ID": "phase6-timeout-request"})

    assert response.status_code == 504
    assert response.json()["error"]["code"] == "REQUEST_TIMEOUT"
    assert response.headers["X-Request-ID"] == "phase6-timeout-request"
    assert len(response.headers["X-Trace-ID"]) == 32
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Cache-Control"] == "no-store"
