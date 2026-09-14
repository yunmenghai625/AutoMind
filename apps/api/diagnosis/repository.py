from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.aigc.repository import UsageSubject
from apps.api.infrastructure.models import DiagnosisRecord, UsageDailyRecord


class DiagnosisRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def reserve_request(self, subject: UsageSubject, limit: int) -> int | None:
        statement = insert(UsageDailyRecord).values(
            date=date.today(),
            subject_key=subject.key,
            user_id=subject.user_id,
            user_kind=subject.kind,
            requests=1,
            text_requests=0,
            aigc_requests=0,
            tokens=0,
            image_calls=0,
            diagnosis_requests=1,
            cost_est_cny=0,
        )
        statement = statement.on_conflict_do_update(
            index_elements=[UsageDailyRecord.date, UsageDailyRecord.subject_key],
            set_={
                "requests": UsageDailyRecord.requests + 1,
                "diagnosis_requests": UsageDailyRecord.diagnosis_requests + 1,
                "updated_at": func.now(),
            },
            where=UsageDailyRecord.diagnosis_requests < limit,
        ).returning(UsageDailyRecord.diagnosis_requests)
        async with self._session.begin():
            used = (await self._session.execute(statement)).scalar_one_or_none()
        return int(used) if used is not None else None

    async def add_usage(
        self, subject: UsageSubject, *, tokens: int, external_call: bool, cost: float
    ) -> None:
        async with self._session.begin():
            await self._session.execute(
                update(UsageDailyRecord)
                .where(
                    UsageDailyRecord.date == date.today(),
                    UsageDailyRecord.subject_key == subject.key,
                )
                .values(
                    tokens=UsageDailyRecord.tokens + tokens,
                    image_calls=UsageDailyRecord.image_calls + int(external_call),
                    cost_est_cny=UsageDailyRecord.cost_est_cny + cost,
                    updated_at=func.now(),
                )
            )

    async def monthly_cost(self) -> float:
        start = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        async with self._session.begin():
            value = await self._session.scalar(
                select(func.coalesce(func.sum(DiagnosisRecord.cost_est_cny), 0)).where(
                    DiagnosisRecord.created_at >= start
                )
            )
        return float(value or Decimal(0))

    async def save(
        self,
        *,
        subject: UsageSubject,
        vehicle_id: UUID,
        agent_run_id: UUID,
        original_file_name: str,
        image_url: str,
        storage_key: str,
        image_sha256: str,
        image_expires_at: datetime,
        mime_type: str,
        warning_type: str,
        confidence: float,
        risk_level: str,
        visible_evidence: list[str],
        uncertainty: str,
        response_text: str,
        citations: list[dict[str, Any]],
        requested_provider: str,
        requested_model: str,
        provider: str,
        model: str,
        status: str,
        latency_ms: int,
        cost_est_cny: float,
        error_code: str | None,
        metadata: dict[str, Any],
    ) -> UUID:
        record_id = uuid4()
        async with self._session.begin():
            self._session.add(
                DiagnosisRecord(
                    id=record_id,
                    user_id=subject.user_id,
                    subject_key=subject.key,
                    vehicle_id=vehicle_id,
                    agent_run_id=agent_run_id,
                    original_file_name=original_file_name[:255],
                    image_url=image_url,
                    storage_key=storage_key,
                    image_sha256=image_sha256,
                    image_expires_at=image_expires_at,
                    mime_type=mime_type,
                    warning_type=warning_type,
                    confidence=confidence,
                    risk_level=risk_level,
                    visible_evidence_json=visible_evidence,
                    uncertainty=uncertainty,
                    response_text=response_text,
                    citations_json=citations,
                    requested_provider=requested_provider,
                    requested_model=requested_model,
                    provider=provider,
                    model=model,
                    status=status,
                    latency_ms=latency_ms,
                    cost_est_cny=cost_est_cny,
                    error_code=error_code,
                    metadata_json=metadata,
                )
            )
        return record_id
