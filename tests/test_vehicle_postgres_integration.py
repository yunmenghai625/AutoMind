import asyncio
import hashlib
import os
from uuid import uuid4

import asyncpg
import pytest
from fastapi.testclient import TestClient

from apps.api.api.dependencies import get_admin_identity
from apps.api.auth.service import AuthIdentity
from apps.api.core.config import Settings
from apps.api.main import create_app
from apps.api.rag.service import NO_EVIDENCE_ANSWER


@pytest.mark.integration
def test_postgres_vehicle_control_persists_and_audits() -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not configured")

    app = create_app(
        Settings(
            app_env="test",
            database_url=database_url,
            database_healthcheck_enabled=True,
        )
    )
    with TestClient(app) as client:
        initial_response = client.get("/api/v1/vehicle/state")
        assert initial_response.status_code == 200
        initial = initial_response.json()["state"]

        target = 23 if initial["climate"]["driver_temp_c"] != 23 else 24
        update_response = client.post(
            "/api/v1/vehicle/control",
            headers={"X-Request-ID": "postgres-integration"},
            json={
                "property": "DRIVER_TEMP",
                "zone": "driver",
                "value": target,
                "expected_version": initial["version"],
            },
        )
        assert update_response.status_code == 200
        updated = update_response.json()["state"]
        assert updated["climate"]["driver_temp_c"] == target
        assert updated["version"] == initial["version"] + 1

        conflict_response = client.post(
            "/api/v1/vehicle/control",
            json={
                "property": "LIGHT_STATE",
                "value": "LOW_BEAM",
                "expected_version": initial["version"],
            },
        )
        assert conflict_response.status_code == 409

        persisted = client.get("/api/v1/vehicle/state").json()["state"]
        assert persisted["climate"]["driver_temp_c"] == target
        assert asyncio.run(_audit_count(database_url, "postgres-integration")) >= 1

        restore_response = client.post(
            "/api/v1/vehicle/control",
            json={
                "property": "DRIVER_TEMP",
                "zone": "driver",
                "value": initial["climate"]["driver_temp_c"],
                "expected_version": persisted["version"],
            },
        )
        assert restore_response.status_code == 200


async def _audit_count(database_url: str, request_id: str) -> int:
    asyncpg_url = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    connection = await asyncpg.connect(asyncpg_url)
    try:
        result = await connection.fetchval(
            "SELECT count(*) FROM vehicle_state_audits WHERE request_id = $1", request_id
        )
        return int(result)
    finally:
        await connection.close()


@pytest.mark.integration
def test_postgres_agent_chain_persists_tools_and_admin_trace() -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not configured")

    app = create_app(Settings(app_env="test", database_url=database_url))
    app.dependency_overrides[get_admin_identity] = lambda: AuthIdentity(
        kind="registered", user_id=uuid4(), role="admin"
    )
    safe_request_id = f"agent-safe-{uuid4()}"
    blocked_request_id = f"agent-blocked-{uuid4()}"
    with TestClient(app) as client:
        initial = client.get("/api/v1/vehicle/state").json()["state"]

        safe = client.post(
            "/api/v1/chat",
            headers={"X-Request-ID": safe_request_id},
            json={"message": "我妈有点冷"},
        )
        assert safe.status_code == 200
        safe_payload = safe.json()
        assert safe_payload["vehicle"]["passengerTemperature"] == 25
        assert safe_payload["vehicle"]["passengerSeatHeat"] == 1
        assert safe_payload["messages"][0]["meta"]["llmCalls"] == 0
        safe_run_id = safe_payload["messages"][0]["meta"]["runId"]

        blocked = client.post(
            "/api/v1/chat",
            headers={"X-Request-ID": blocked_request_id},
            json={"message": "120km/h开门"},
        )
        assert blocked.status_code == 200
        assert blocked.json()["messages"][0]["meta"]["blocked"] is True

        detail = client.get(f"/api/v1/admin/agent-runs/{safe_run_id}")
        assert detail.status_code == 200
        assert detail.json()["query"] == "我妈有点冷"
        assert set(detail.json()["toolsUsed"]) == {"set_temperature", "set_seat_heating"}

        persisted = client.get("/api/v1/vehicle/state").json()["state"]
        restore_temperature = client.post(
            "/api/v1/vehicle/control",
            json={
                "property": "PASSENGER_TEMP",
                "zone": "passenger",
                "value": initial["climate"]["passenger_temp_c"],
                "expected_version": persisted["version"],
            },
        )
        assert restore_temperature.status_code == 200
        restored_once = restore_temperature.json()["state"]
        restore_heat = client.post(
            "/api/v1/vehicle/control",
            json={
                "property": "SEAT_HEAT",
                "zone": "passenger",
                "value": initial["seat_heat"]["passenger"],
                "expected_version": restored_once["version"],
            },
        )
        assert restore_heat.status_code == 200

    safe_count, blocked_count = asyncio.run(
        _agent_tool_counts(database_url, safe_request_id, blocked_request_id)
    )
    assert safe_count == 2
    assert blocked_count == 1


async def _agent_tool_counts(
    database_url: str, safe_request_id: str, blocked_request_id: str
) -> tuple[int, int]:
    asyncpg_url = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    connection = await asyncpg.connect(asyncpg_url)
    try:
        safe_count = await connection.fetchval(
            """
            SELECT count(*) FROM tool_calls tc
            JOIN agent_runs ar ON ar.id = tc.run_id
            WHERE ar.request_id = $1 AND tc.status = 'success'
            """,
            safe_request_id,
        )
        blocked_count = await connection.fetchval(
            """
            SELECT count(*) FROM tool_calls tc
            JOIN agent_runs ar ON ar.id = tc.run_id
            WHERE ar.request_id = $1 AND tc.status = 'blocked'
            """,
            blocked_request_id,
        )
        return int(safe_count), int(blocked_count)
    finally:
        await connection.close()


@pytest.mark.integration
def test_postgres_rag_ingests_retrieves_cites_and_audits() -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not configured")

    source_key = f"phase3-integration-{uuid4()}"
    request_id = f"rag-query-{uuid4()}"
    no_evidence_request_id = f"rag-no-evidence-{uuid4()}"
    app = create_app(Settings(app_env="test", database_url=database_url))
    app.dependency_overrides[get_admin_identity] = lambda: AuthIdentity(
        kind="registered", user_id=uuid4(), role="admin"
    )
    try:
        with TestClient(app) as client:
            ingested = client.post(
                "/api/v1/knowledge/documents/ingest",
                json={
                    "sourceKey": source_key,
                    "title": "Phase 3 Integration Manual",
                    "description": "PostgreSQL hybrid retrieval integration fixture",
                    "content": (
                        "<!-- page: 217 -->\n## TPMS专用测试章节\n"
                        "Phase3专用胎压测试码：胎压报警灯点亮后，先减速并在安全地点停车，"
                        "再检查四条轮胎气压。"
                    ),
                },
            )
            assert ingested.status_code == 200
            assert ingested.json()["status"] == "indexed"

            queried = client.post(
                "/api/v1/knowledge/query",
                headers={"X-Request-ID": request_id},
                json={"query": "Phase3专用胎压测试码亮了怎么办"},
            )
            assert queried.status_code == 200
            payload = queried.json()
            assert payload["citations"][0]["source"] == "Phase 3 Integration Manual"
            assert payload["citations"][0]["chapter"] == "TPMS专用测试章节"
            assert payload["citations"][0]["page"] == 217

            no_evidence = client.post(
                "/api/v1/knowledge/query",
                headers={"X-Request-ID": no_evidence_request_id},
                json={"query": "月球背面咖啡豆烘焙气压标准"},
            )
            assert no_evidence.status_code == 200
            assert no_evidence.json()["answer"] == NO_EVIDENCE_ANSWER
            assert no_evidence.json()["citations"] == []

        statuses = asyncio.run(
            _rag_query_statuses(database_url, [request_id, no_evidence_request_id])
        )
        assert statuses == {request_id: "success", no_evidence_request_id: "no_evidence"}
    finally:
        asyncio.run(
            _cleanup_rag_integration(
                database_url,
                source_key,
                [request_id, no_evidence_request_id],
            )
        )


async def _rag_query_statuses(database_url: str, request_ids: list[str]) -> dict[str, str]:
    asyncpg_url = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    connection = await asyncpg.connect(asyncpg_url)
    try:
        rows = await connection.fetch(
            "SELECT request_id, status FROM rag_queries WHERE request_id = ANY($1::text[])",
            request_ids,
        )
        return {row["request_id"]: row["status"] for row in rows}
    finally:
        await connection.close()


async def _cleanup_rag_integration(
    database_url: str, source_key: str, request_ids: list[str]
) -> None:
    asyncpg_url = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    connection = await asyncpg.connect(asyncpg_url)
    try:
        await connection.execute("DELETE FROM documents WHERE source_key = $1", source_key)
        await connection.execute(
            "DELETE FROM rag_queries WHERE request_id = ANY($1::text[])", request_ids
        )
    finally:
        await connection.close()


@pytest.mark.integration
def test_postgres_aigc_preview_cache_apply_and_metrics(tmp_path) -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not configured")

    guest_id = f"phase35-{uuid4()}"
    subject_key = f"guest:{hashlib.sha256(guest_id.encode()).hexdigest()}"
    generate_request_id = f"aigc-generate-{uuid4()}"
    cached_request_id = f"aigc-cache-{uuid4()}"
    apply_request_id = f"aigc-apply-{uuid4()}"
    app = create_app(
        Settings(
            app_env="test",
            database_url=database_url,
            aigc_guest_daily_limit=3,
            aigc_local_asset_dir=str(tmp_path),
            rag_max_retries=0,
        )
    )
    app.dependency_overrides[get_admin_identity] = lambda: AuthIdentity(
        kind="registered", user_id=uuid4(), role="admin"
    )
    headers = {"X-Guest-ID": guest_id}
    try:
        with TestClient(app) as client:
            initial = client.get("/api/v1/vehicle/state").json()["state"]
            prompt = "给我一个适合海边夜间驾驶的安静主题"
            generated = client.post(
                "/api/v1/aigc/themes",
                headers={**headers, "X-Request-ID": generate_request_id},
                json={"prompt": prompt},
            )
            assert generated.status_code == 200, generated.text
            preview = generated.json()
            assert preview["theme_spec"]["name"] == "静谧海岸"
            assert preview["metadata"]["provider"] == "local"
            assert preview["metadata"]["image_provider"] == "mock"
            assert preview["metadata"]["cost_est_cny"] == 0

            unchanged = client.get("/api/v1/vehicle/state").json()["state"]
            assert unchanged["version"] == initial["version"]

            cached = client.post(
                "/api/v1/aigc/themes",
                headers={**headers, "X-Request-ID": cached_request_id},
                json={"prompt": prompt},
            )
            assert cached.status_code == 200
            assert cached.json()["metadata"]["cached"] is True

            applied = client.post(
                f"/api/v1/aigc/themes/{preview['theme_id']}/apply",
                headers={**headers, "X-Request-ID": apply_request_id},
                json={"confirmed": True, "expected_version": unchanged["version"]},
            )
            assert applied.status_code == 200, applied.text
            assert applied.json()["vehicle_state_version"] == unchanged["version"] + 2

            changed = client.get("/api/v1/vehicle/state").json()["state"]
            assert changed["climate"]["driver_temp_c"] == 22
            assert changed["climate"]["passenger_temp_c"] == 22

            metrics = client.get("/api/v1/aigc/metrics")
            assert metrics.status_code == 200
            assert metrics.json()["generation_count"] >= 2

            restore_driver = client.post(
                "/api/v1/vehicle/control",
                json={
                    "property": "DRIVER_TEMP",
                    "zone": "driver",
                    "value": initial["climate"]["driver_temp_c"],
                    "expected_version": changed["version"],
                },
            )
            restored = restore_driver.json()["state"]
            client.post(
                "/api/v1/vehicle/control",
                json={
                    "property": "PASSENGER_TEMP",
                    "zone": "passenger",
                    "value": initial["climate"]["passenger_temp_c"],
                    "expected_version": restored["version"],
                },
            )

        generation_count, tool_count, usage_requests = asyncio.run(
            _aigc_evidence(database_url, subject_key, apply_request_id)
        )
        assert generation_count == 2
        assert tool_count == 2
        assert usage_requests == 2
    finally:
        asyncio.run(
            _cleanup_aigc_integration(
                database_url,
                subject_key,
                apply_request_id,
                [generate_request_id, cached_request_id],
            )
        )


async def _aigc_evidence(
    database_url: str, subject_key: str, apply_request_id: str
) -> tuple[int, int, int]:
    asyncpg_url = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    connection = await asyncpg.connect(asyncpg_url)
    try:
        generation_count = await connection.fetchval(
            "SELECT count(*) FROM aigc_generations WHERE subject_key = $1", subject_key
        )
        tool_count = await connection.fetchval(
            """
            SELECT count(*) FROM tool_calls tc
            JOIN agent_runs ar ON ar.id = tc.run_id
            WHERE ar.request_id = $1 AND tc.status = 'success'
            """,
            apply_request_id,
        )
        usage_requests = await connection.fetchval(
            "SELECT requests FROM usage_daily WHERE subject_key = $1", subject_key
        )
        return int(generation_count), int(tool_count), int(usage_requests)
    finally:
        await connection.close()


async def _cleanup_aigc_integration(
    database_url: str,
    subject_key: str,
    apply_request_id: str,
    rag_parent_request_ids: list[str],
) -> None:
    asyncpg_url = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    connection = await asyncpg.connect(asyncpg_url)
    try:
        await connection.execute("DELETE FROM aigc_generations WHERE subject_key = $1", subject_key)
        await connection.execute("DELETE FROM usage_daily WHERE subject_key = $1", subject_key)
        await connection.execute("DELETE FROM agent_runs WHERE request_id = $1", apply_request_id)
        rag_ids = [f"aigc-rag-{request_id}"[:128] for request_id in rag_parent_request_ids]
        await connection.execute(
            "DELETE FROM rag_queries WHERE request_id = ANY($1::text[])", rag_ids
        )
    finally:
        await connection.close()
