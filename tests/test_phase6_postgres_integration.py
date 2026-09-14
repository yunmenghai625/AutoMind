import asyncio
import os
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import asyncpg
import jwt
import pytest
from fastapi.testclient import TestClient

from apps.api.core.config import Settings
from apps.api.main import create_app

JWT_SECRET = "phase6-integration-secret-with-at-least-32-bytes"


def _token(user_id: UUID, role: str) -> str:
    return jwt.encode(
        {
            "sub": str(user_id),
            "email": f"{role}@example.com",
            "role": role,
            "aud": "authenticated",
            "exp": datetime.now(UTC) + timedelta(minutes=10),
        },
        JWT_SECRET,
        algorithm="HS256",
    )


@pytest.mark.integration
def test_admin_uses_real_metrics_rbac_and_request_correlation() -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not configured")

    admin_id, user_id = uuid4(), uuid4()
    prefix = f"phase6-{uuid4()}"
    request_ids = {
        name: f"{prefix}-{name}"
        for name in (
            "failed",
            "anonymous",
            "user",
            "overview",
            "lookup",
            "operational",
            "budget",
            "components",
        )
    }
    admin_headers = {"Authorization": f"Bearer {_token(admin_id, 'admin')}"}
    user_headers = {"Authorization": f"Bearer {_token(user_id, 'authenticated')}"}
    app = create_app(
        Settings(
            app_env="test",
            database_url=database_url,
            jwt_secret=JWT_SECRET,
            redis_url="redis://localhost:6379/0",
            rate_limit_enabled=True,
            operational_metrics_persistence_enabled=True,
        )
    )

    try:
        with TestClient(app) as client:
            failed = client.post(
                "/api/v1/vehicle/control",
                headers={"X-Request-ID": request_ids["failed"]},
                json={},
            )
            assert failed.status_code == 422
            failed_trace_id = failed.headers["X-Trace-ID"]

            anonymous = client.get(
                "/api/v1/admin/overview",
                headers={"X-Request-ID": request_ids["anonymous"]},
            )
            assert anonymous.status_code == 401

            forbidden = client.get(
                "/api/v1/admin/overview",
                headers={**user_headers, "X-Request-ID": request_ids["user"]},
            )
            assert forbidden.status_code == 403

            overview = client.get(
                "/api/v1/admin/overview",
                headers={**admin_headers, "X-Request-ID": request_ids["overview"]},
            )
            assert overview.status_code == 200, overview.text
            assert overview.json()["requests"] >= 3
            assert "generatedAt" in overview.json()

            located = client.get(
                f"/api/v1/admin/requests/{request_ids['failed']}",
                headers={**admin_headers, "X-Request-ID": request_ids["lookup"]},
            )
            assert located.status_code == 200, located.text
            assert located.json()["traceId"] == failed_trace_id
            assert located.json()["statusCode"] == 422
            assert located.json()["errorCode"] == "VALIDATION_ERROR"

            operational = client.get(
                "/api/v1/admin/operational-metrics",
                headers={**admin_headers, "X-Request-ID": request_ids["operational"]},
            )
            assert operational.status_code == 200
            assert set(operational.json()) == {"agent", "tool", "rag"}

            budget = client.get(
                "/api/v1/admin/budget",
                headers={**admin_headers, "X-Request-ID": request_ids["budget"]},
            )
            assert budget.status_code == 200
            assert budget.json()["state"] in {"normal", "economy", "exhausted"}

            components = client.get(
                "/api/v1/admin/components",
                headers={**admin_headers, "X-Request-ID": request_ids["components"]},
            )
            assert components.status_code == 200
            by_name = {item["name"]: item for item in components.json()}
            assert by_name["Database"]["status"] == "operational"
            assert by_name["Rate Limiter"]["status"] == "operational"
    finally:
        asyncio.run(_cleanup(database_url, [admin_id, user_id], list(request_ids.values())))


async def _cleanup(database_url: str, user_ids: list[UUID], request_ids: list[str]) -> None:
    connection = await asyncpg.connect(
        database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    )
    try:
        await connection.execute(
            "DELETE FROM http_request_metrics WHERE request_id = ANY($1::text[])", request_ids
        )
        await connection.execute("DELETE FROM users WHERE id = ANY($1::uuid[])", user_ids)
    finally:
        await connection.close()
