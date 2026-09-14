import asyncio
import hashlib
import os
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import asyncpg
import jwt
import pytest
from fastapi.testclient import TestClient

from apps.api.core.config import Settings
from apps.api.main import create_app

JWT_SECRET = "phase5-test-secret-with-at-least-32-bytes"


def _token(user_id: UUID, email: str) -> str:
    return jwt.encode(
        {
            "sub": str(user_id),
            "email": email,
            "role": "authenticated",
            "aud": "authenticated",
            "exp": datetime.now(UTC) + timedelta(minutes=10),
        },
        JWT_SECRET,
        algorithm="HS256",
    )


@pytest.mark.integration
def test_product_system_isolates_users_masks_vin_and_enforces_quotas() -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not configured")

    user_a = uuid4()
    user_b = uuid4()
    guest_id = f"phase5-guest-{uuid4()}"
    request_ids = [f"phase5-run-{uuid4()}" for _ in range(3)]
    auth_a = {"Authorization": f"Bearer {_token(user_a, 'a@example.com')}"}
    auth_b = {"Authorization": f"Bearer {_token(user_b, 'b@example.com')}"}
    app = create_app(
        Settings(
            app_env="test",
            database_url=database_url,
            jwt_secret=JWT_SECRET,
            guest_text_daily_limit=1,
            registered_text_daily_limit=2,
            usage_quota_enabled=True,
            vehicle_data_provider="disabled",
            vin_hash_secret="phase5-vin-secret",
        )
    )

    try:
        with TestClient(app) as client:
            me = client.get("/api/v1/auth/me", headers=auth_a)
            assert me.status_code == 200
            assert me.json()["user_id"] == str(user_a)

            preference = {
                "preferredTemperature": 24,
                "seatHeatingLevel": 2,
                "preferredChargingLimit": 85,
                "preferredDrivingMode": "Eco",
                "extensions": {"source": "explicit-settings-form"},
            }
            saved = client.put("/api/v1/preferences", headers=auth_a, json=preference)
            assert saved.status_code == 200, saved.text
            assert saved.json()["preferredTemperature"] == 24
            assert (
                client.get("/api/v1/preferences", headers=auth_b).json()["preferredTemperature"]
                == 23
            )

            raw_vin = "1HGCM82633A004352"
            created = client.post(
                "/api/v1/garage/vehicles",
                headers=auth_a,
                json={
                    "make": "AutoMind",
                    "model": "X1",
                    "year": 2026,
                    "powertrain": "BEV",
                    "mileage_km": 12842,
                    "vin": raw_vin,
                },
            )
            assert created.status_code == 201, created.text
            vehicle_id = created.json()["id"]
            assert created.json()["vinMasked"] == "*************4352"
            assert raw_vin not in created.text

            hidden = client.get(f"/api/v1/garage/vehicles/{vehicle_id}", headers=auth_b)
            assert hidden.status_code == 404
            assert client.get("/api/v1/garage/vehicles", headers=auth_b).json() == []

            recalls = client.get("/api/v1/vehicle/recalls", headers=auth_a)
            assert recalls.status_code == 200
            assert recalls.json()["status"] == "unavailable"
            assert recalls.json()["recalls"] == []

            run_ids: list[str] = []
            for index in range(2):
                response = client.post(
                    "/api/v1/chat",
                    headers={**auth_a, "X-Request-ID": request_ids[index]},
                    json={"message": "电量还有多少"},
                )
                assert response.status_code == 200, response.text
                run_ids.append(response.json()["messages"][0]["meta"]["runId"])
            exhausted = client.post(
                "/api/v1/chat",
                headers=auth_a,
                json={"message": "电量还有多少"},
            )
            assert exhausted.status_code == 429

            guest_first = client.post(
                "/api/v1/chat",
                headers={"X-Guest-ID": guest_id, "X-Request-ID": request_ids[2]},
                json={"message": "电量还有多少"},
            )
            assert guest_first.status_code == 200, guest_first.text
            guest_second = client.post(
                "/api/v1/chat",
                headers={"X-Guest-ID": guest_id},
                json={"message": "电量还有多少"},
            )
            assert guest_second.status_code == 429

            feedback = client.post(
                "/api/v1/feedback",
                headers=auth_a,
                json={"run_id": run_ids[0], "rating": 1, "reason": "helpful"},
            )
            assert feedback.status_code == 201, feedback.text
            assert len(client.get("/api/v1/feedback", headers=auth_a).json()) == 1
            assert client.get("/api/v1/feedback", headers=auth_b).json() == []

            deleted = client.delete("/api/v1/preferences", headers=auth_a)
            assert deleted.status_code == 200
            assert deleted.json()["deleted"] is True
            assert (
                client.get("/api/v1/preferences", headers=auth_a).json()["preferredTemperature"]
                == 23
            )

        stored = asyncio.run(_stored_product_data(database_url, user_a, UUID(vehicle_id), guest_id))
        assert stored["vin_hash"] != raw_vin
        assert stored["vin_last4"] == "4352"
        assert stored["user_a_text"] == 2
        assert stored["guest_text"] == 1
    finally:
        asyncio.run(_cleanup(database_url, user_a, user_b, guest_id, request_ids))


async def _stored_product_data(
    database_url: str, user_id: UUID, vehicle_id: UUID, guest_id: str
) -> dict[str, Any]:
    connection = await asyncpg.connect(
        database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    )
    try:
        vehicle = await connection.fetchrow(
            "SELECT vin_hash, vin_last4 FROM vehicles WHERE id = $1", vehicle_id
        )
        assert vehicle is not None
        guest_subject = "guest:" + hashlib.sha256(guest_id.encode()).hexdigest()
        guest_count = await connection.fetchval(
            "SELECT text_requests FROM usage_daily WHERE subject_key = $1", guest_subject
        )
        user_count = await connection.fetchval(
            "SELECT text_requests FROM usage_daily WHERE user_id = $1", user_id
        )
        return {
            "vin_hash": vehicle["vin_hash"],
            "vin_last4": vehicle["vin_last4"],
            "user_a_text": int(user_count),
            "guest_text": int(guest_count),
        }
    finally:
        await connection.close()


async def _cleanup(
    database_url: str,
    user_a: UUID,
    user_b: UUID,
    guest_id: str,
    request_ids: list[str],
) -> None:
    connection = await asyncpg.connect(
        database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    )
    guest_subject = "guest:" + hashlib.sha256(guest_id.encode()).hexdigest()
    try:
        await connection.execute(
            "DELETE FROM agent_runs WHERE request_id = ANY($1::text[])", request_ids
        )
        await connection.execute(
            "DELETE FROM usage_daily WHERE user_id = ANY($1::uuid[]) OR subject_key = $2",
            [user_a, user_b],
            guest_subject,
        )
        await connection.execute("DELETE FROM users WHERE id = ANY($1::uuid[])", [user_a, user_b])
    finally:
        await connection.close()
