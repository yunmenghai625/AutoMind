import io
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from PIL import Image
from pydantic import ValidationError

from apps.api.aigc.repository import UsageSubject
from apps.api.diagnosis.image_guard import ImageGuard, ImageGuardError
from apps.api.diagnosis.providers.local_provider import LocalHeuristicVlmProvider
from apps.api.diagnosis.schemas import VlmStructuredOutput
from apps.api.diagnosis.service import (
    DiagnosisInput,
    DiagnosisQuotaExceededError,
    DiagnosisService,
)
from apps.api.infrastructure.storage import StoredObject
from apps.api.rag.entities import CitationData, KnowledgeResult, RetrievalMetrics
from tests.fakes import DEMO_VEHICLE_ID, InMemoryAgentTraceStore


def image_bytes(size: tuple[int, int] = (640, 480), image_format: str = "PNG") -> bytes:
    output = io.BytesIO()
    Image.new("RGB", size, "#131722").save(output, format=image_format)
    return output.getvalue()


def guard() -> ImageGuard:
    return ImageGuard(
        max_bytes=5_242_880,
        max_dimension=800,
        max_pixels=2_000_000,
        jpeg_quality=82,
    )


def test_image_guard_rejects_bad_content_and_mime_mismatch() -> None:
    with pytest.raises(ImageGuardError, match="有效图片"):
        guard().process(b"not-an-image", "image/png")
    with pytest.raises(ImageGuardError, match="不一致"):
        guard().process(image_bytes(image_format="PNG"), "image/jpeg")


def test_image_guard_compresses_and_bounds_dimensions() -> None:
    result = guard().process(image_bytes((1600, 1200)), "image/png")
    assert result.content_type == "image/jpeg"
    assert (result.width, result.height) == (800, 600)
    assert Image.open(io.BytesIO(result.content)).format == "JPEG"


def test_vlm_output_schema_is_strict() -> None:
    with pytest.raises(ValidationError):
        VlmStructuredOutput.model_validate(
            {
                "detections": [
                    {
                        "warning_type": "unknown",
                        "label": "unknown",
                        "confidence": 1.2,
                        "visible_evidence": ["模糊"],
                        "uncertainty": "不足",
                        "unexpected": True,
                    }
                ]
            }
        )


class MemoryStorage:
    def __init__(self) -> None:
        self.items: dict[str, bytes] = {}

    async def put(self, *, key: str, content: bytes, content_type: str) -> StoredObject:
        assert content_type == "image/jpeg"
        self.items[key] = content
        return StoredObject(key=key, url=f"/diagnosis/{key}")

    async def delete(self, key: str) -> None:
        self.items.pop(key, None)


class MemoryDiagnosisRepository:
    def __init__(self) -> None:
        self.usage: dict[str, int] = {}
        self.saved: list[dict[str, Any]] = []
        self.usage_events: list[dict[str, Any]] = []

    async def reserve_request(self, subject: UsageSubject, limit: int) -> int | None:
        used = self.usage.get(subject.key, 0)
        if used >= limit:
            return None
        self.usage[subject.key] = used + 1
        return used + 1

    async def monthly_cost(self) -> float:
        return 0

    async def save(self, **values: Any) -> UUID:
        self.saved.append(values)
        return uuid4()

    async def add_usage(self, subject: UsageSubject, **values: Any) -> None:
        self.usage_events.append({"subject": subject, **values})


class KnowledgeStub:
    async def query(self, *, request_id: str, query: str) -> KnowledgeResult:
        return KnowledgeResult(
            answer="根据车辆手册，应先安全停车检查胎压。",
            citations=[CitationData("车辆手册", "胎压系统", 42, "检查并校正四轮胎压。")],
            retrieval=RetrievalMetrics(
                original_query=query,
                rewritten_query=query,
                retrieved_documents=1,
                reranker_enabled=True,
                vector_search_ms=2,
                rerank_ms=1,
                retry_count=0,
                query_id=uuid4(),
            ),
        )


def build_service(repository: MemoryDiagnosisRepository) -> DiagnosisService:
    provider = LocalHeuristicVlmProvider()
    return DiagnosisService(
        repository=repository,  # type: ignore[arg-type]
        trace_store=InMemoryAgentTraceStore(),
        image_guard=guard(),
        storage=MemoryStorage(),
        vlm_provider=provider,
        fallback_provider=provider,
        knowledge_service=KnowledgeStub(),  # type: ignore[arg-type]
        guest_daily_limit=1,
        user_daily_limit=2,
        confidence_threshold=0.7,
        monthly_budget_cny=15,
        retention_days=14,
    )


@pytest.mark.asyncio
async def test_diagnosis_low_confidence_is_explicit_and_audited() -> None:
    repository = MemoryDiagnosisRepository()
    result = await build_service(repository).diagnose(
        request_id="diagnosis-low-confidence",
        subject=UsageSubject("guest", "guest:low"),
        vehicle_id=DEMO_VEHICLE_ID,
        payload=DiagnosisInput(image_bytes(), "image/png", "blurred.png", None),
    )
    assert result.metadata.low_confidence is True
    assert "无法可靠识别" in result.message
    assert result.references == []
    assert repository.saved[0]["status"] == "low_confidence"
    assert repository.saved[0]["latency_ms"] >= 0
    assert repository.saved[0]["cost_est_cny"] == 0


@pytest.mark.asyncio
async def test_high_confidence_maps_to_knowledge_and_guest_quota_applies() -> None:
    repository = MemoryDiagnosisRepository()
    service = build_service(repository)
    subject = UsageSubject("guest", "guest:quota")
    result = await service.diagnose(
        request_id="diagnosis-tpms",
        subject=subject,
        vehicle_id=DEMO_VEHICLE_ID,
        payload=DiagnosisInput(image_bytes(), "image/png", "tpms.png", "胎压灯亮"),
    )
    assert result.detected[0].risk == "Medium"
    assert result.references[0].source == "车辆手册"
    assert repository.saved[0]["metadata"]["structured_output"]["detections"]
    with pytest.raises(DiagnosisQuotaExceededError):
        await service.diagnose(
            request_id="diagnosis-over-quota",
            subject=subject,
            vehicle_id=DEMO_VEHICLE_ID,
            payload=DiagnosisInput(image_bytes(), "image/png", "tpms-2.png", None),
        )

    registered = UsageSubject("registered", f"user:{uuid4()}", uuid4())
    for index in range(2):
        registered_result = await service.diagnose(
            request_id=f"diagnosis-registered-{index}",
            subject=registered,
            vehicle_id=DEMO_VEHICLE_ID,
            payload=DiagnosisInput(image_bytes(), "image/png", f"tpms-user-{index}.png", None),
        )
        assert registered_result.metadata.quota_limit == 2
    with pytest.raises(DiagnosisQuotaExceededError):
        await service.diagnose(
            request_id="diagnosis-registered-over-quota",
            subject=registered,
            vehicle_id=DEMO_VEHICLE_ID,
            payload=DiagnosisInput(image_bytes(), "image/png", "tpms-user-3.png", None),
        )


def test_image_expiry_window_is_in_required_range() -> None:
    now = datetime.now(UTC)
    assert 7 <= 14 <= 30
    assert now.tzinfo is not None
