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

JWT_SECRET = "phase7-integration-secret-with-at-least-32-bytes"
LOAD_TEST_TOKEN = "phase7-load-test-secret"


def _admin_token(user_id: UUID) -> str:
    return jwt.encode(
        {
            "sub": str(user_id),
            "email": "phase7-admin@example.com",
            "role": "admin",
            "aud": "authenticated",
            "exp": datetime.now(UTC) + timedelta(minutes=10),
        },
        JWT_SECRET,
        algorithm="HS256",
    )


@pytest.mark.integration
def test_authenticated_load_test_traffic_is_separated_from_user_traffic() -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not configured")

    admin_id = uuid4()
    prefix = f"phase7-{uuid4()}"
    request_ids = [f"{prefix}-{name}" for name in ("load", "spoof", "lookup-load", "lookup-spoof")]
    app = create_app(
        Settings(
            app_env="test",
            database_url=database_url,
            jwt_secret=JWT_SECRET,
            redis_url="redis://localhost:6379/0",
            load_test_token=LOAD_TEST_TOKEN,
        )
    )
    admin = {"Authorization": f"Bearer {_admin_token(admin_id)}"}

    try:
        with TestClient(app) as client:
            load = client.get(
                "/health",
                headers={
                    "X-Request-ID": request_ids[0],
                    "X-AutoMind-Traffic-Class": "load_test",
                    "X-Load-Test-Token": LOAD_TEST_TOKEN,
                },
            )
            assert load.status_code == 200

            spoof = client.get(
                "/health",
                headers={
                    "X-Request-ID": request_ids[1],
                    "X-AutoMind-Traffic-Class": "load_test",
                    "X-Load-Test-Token": "wrong-token",
                },
            )
            assert spoof.status_code == 200

            located_load = client.get(
                f"/api/v1/admin/requests/{request_ids[0]}",
                headers={**admin, "X-Request-ID": request_ids[2]},
            )
            assert located_load.status_code == 200
            assert located_load.json()["trafficClass"] == "load_test"

            located_spoof = client.get(
                f"/api/v1/admin/requests/{request_ids[1]}",
                headers={**admin, "X-Request-ID": request_ids[3]},
            )
            assert located_spoof.status_code == 200
            assert located_spoof.json()["trafficClass"] == "user"
    finally:
        asyncio.run(_cleanup(database_url, admin_id, request_ids))


async def _cleanup(database_url: str, admin_id: UUID, request_ids: list[str]) -> None:
    connection = await asyncpg.connect(
        database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    )
    try:
        await connection.execute(
            "DELETE FROM http_request_metrics WHERE request_id = ANY($1::text[])", request_ids
        )
        await connection.execute("DELETE FROM users WHERE id = $1", admin_id)
    finally:
        await connection.close()
