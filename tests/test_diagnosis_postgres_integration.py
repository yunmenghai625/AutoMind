import asyncio
import io
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

import asyncpg
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from apps.api.core.config import Settings
from apps.api.main import create_app


def _png_bytes() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (720, 480), "#111827").save(output, format="PNG")
    return output.getvalue()


@pytest.mark.integration
def test_postgres_diagnosis_persists_metrics_and_enforces_guest_quota(
    tmp_path: Path,
) -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not configured")

    guest_id = f"phase4-{uuid4()}"
    request_id = f"diagnosis-{uuid4()}"
    settings = Settings(
        app_env="test",
        database_url=database_url,
        diagnosis_local_asset_dir=str(tmp_path),
        guest_image_daily_limit=1,
        vlm_provider="local",
    )
    app = create_app(settings)
    with TestClient(app) as client:
        invalid = client.post(
            "/api/v1/diagnosis",
            headers={"X-Guest-ID": f"invalid-{guest_id}"},
            files={"file": ("bad.png", b"not-an-image", "image/png")},
        )
        assert invalid.status_code == 422
        assert invalid.json()["error"]["code"] == "INVALID_IMAGE"

        first = client.post(
            "/api/v1/diagnosis",
            headers={"X-Guest-ID": guest_id, "X-Request-ID": request_id},
            files={"file": ("tpms-warning.png", _png_bytes(), "image/png")},
            data={"description": "仪表显示胎压警告灯"},
        )
        assert first.status_code == 200, first.text
        payload = first.json()
        assert payload["request_id"] == request_id
        assert payload["detected"][0]["code"] == "TPMS"
        assert payload["metadata"]["latency_ms"] >= 0
        assert payload["metadata"]["cost_est_cny"] == 0
        assert payload["metadata"]["quota_used"] == 1

        second = client.post(
            "/api/v1/diagnosis",
            headers={"X-Guest-ID": guest_id},
            files={"file": ("tpms-warning-2.png", _png_bytes(), "image/png")},
        )
        assert second.status_code == 429
        assert second.json()["error"]["code"] == "DIAGNOSIS_DAILY_QUOTA_EXCEEDED"

    stored = asyncio.run(_read_and_cleanup(database_url, request_id, tmp_path))
    assert stored["provider"] == "local"
    assert stored["warning_type"] == "tire_pressure"
    assert stored["latency_ms"] >= 0
    assert float(stored["cost_est_cny"]) == 0
    assert stored["diagnosis_requests"] == 1
    assert stored["image_calls"] == 0
    assert not any(tmp_path.iterdir())


async def _read_and_cleanup(database_url: str, request_id: str, asset_dir: Path) -> dict[str, Any]:
    asyncpg_url = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    connection = await asyncpg.connect(asyncpg_url)
    try:
        row = await connection.fetchrow(
            """
            SELECT d.provider, d.warning_type, d.latency_ms, d.cost_est_cny,
                   d.storage_key, d.subject_key, u.diagnosis_requests, u.image_calls,
                   d.agent_run_id
            FROM diagnosis_records d
            JOIN usage_daily u ON u.subject_key = d.subject_key
            JOIN agent_runs a ON a.id = d.agent_run_id
            WHERE a.request_id = $1
            """,
            request_id,
        )
        assert row is not None
        values = dict(row)
        await connection.execute(
            "DELETE FROM diagnosis_records WHERE agent_run_id = $1", values["agent_run_id"]
        )
        await connection.execute("DELETE FROM agent_runs WHERE id = $1", values["agent_run_id"])
        await connection.execute(
            "DELETE FROM usage_daily WHERE subject_key = $1", values["subject_key"]
        )
        storage_key = Path(values["storage_key"]).name
        test_asset = (asset_dir / storage_key).resolve()
        if test_asset.parent == asset_dir.resolve() and test_asset.is_file():
            test_asset.unlink()
        return values
    finally:
        await connection.close()
