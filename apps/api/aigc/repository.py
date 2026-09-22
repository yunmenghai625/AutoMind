from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import case, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.aigc.schemas import ThemeSpec
from apps.api.infrastructure.models import (
    AigcGenerationRecord,
    CockpitThemeRecord,
    UsageDailyRecord,
)


@dataclass(frozen=True, slots=True)
class UsageSubject:
    kind: str
    key: str
    user_id: UUID | None = None
    role: str = "guest"

    @property
    def vehicle_user_id(self) -> UUID | None:
        """Admins operate the isolated demo vehicle, never another user's vehicle."""
        return None if self.role == "admin" else self.user_id


@dataclass(frozen=True, slots=True)
class StoredTheme:
    id: UUID
    generation_id: UUID
    spec: ThemeSpec
    wallpaper_url: str | None
    subject_key: str
    prompt_hash: str
    vehicle_id: UUID


class AigcRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def reserve_daily_request(self, subject: UsageSubject, limit: int) -> int | None:
        today = date.today()
        statement = insert(UsageDailyRecord).values(
            date=today,
            subject_key=subject.key,
            user_id=subject.user_id,
            user_kind=subject.kind,
            requests=1,
            text_requests=0,
            aigc_requests=1,
            tokens=0,
            image_calls=0,
            cost_est_cny=0,
        )
        statement = statement.on_conflict_do_update(
            index_elements=[UsageDailyRecord.date, UsageDailyRecord.subject_key],
            set_={
                "requests": UsageDailyRecord.requests + 1,
                "aigc_requests": UsageDailyRecord.aigc_requests + 1,
                "updated_at": func.now(),
            },
            where=UsageDailyRecord.aigc_requests < limit,
        ).returning(UsageDailyRecord.aigc_requests)
        async with self._session.begin():
            used = (await self._session.execute(statement)).scalar_one_or_none()
        return int(used) if used is not None else None

    async def add_usage(
        self, subject: UsageSubject, *, tokens: int, image_calls: int, cost: float
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
                    image_calls=UsageDailyRecord.image_calls + image_calls,
                    cost_est_cny=UsageDailyRecord.cost_est_cny + cost,
                    updated_at=func.now(),
                )
            )

    async def monthly_external_image_cost(self) -> float:
        start = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        async with self._session.begin():
            value = await self._session.scalar(
                select(func.coalesce(func.sum(AigcGenerationRecord.image_cost_est_cny), 0)).where(
                    AigcGenerationRecord.created_at >= start,
                    AigcGenerationRecord.image_provider.is_not(None),
                    AigcGenerationRecord.image_provider != "mock",
                )
            )
        return float(value or Decimal(0))

    async def find_cached(self, subject: UsageSubject, prompt_hash: str) -> StoredTheme | None:
        async with self._session.begin():
            record = await self._session.scalar(
                select(CockpitThemeRecord)
                .where(
                    CockpitThemeRecord.subject_key == subject.key,
                    CockpitThemeRecord.prompt_hash == prompt_hash,
                )
                .order_by(CockpitThemeRecord.created_at.desc())
                .limit(1)
            )
        return self._to_stored(record) if record else None

    async def save_generation(
        self,
        *,
        subject: UsageSubject,
        vehicle_id: UUID,
        user_prompt: str,
        enhanced_prompt: str,
        prompt_hash: str,
        provider: str,
        model: str,
        image_provider: str | None,
        image_model: str | None,
        status: str,
        latency_ms: int,
        cost_est_cny: float,
        image_cost_est_cny: float,
        wallpaper_url: str | None,
        cached: bool,
        regenerated: bool,
        degraded_reason: str | None,
        metadata: dict[str, Any],
        spec: ThemeSpec,
    ) -> StoredTheme:
        generation_id = uuid4()
        theme_id = uuid4()
        async with self._session.begin():
            self._session.add(
                AigcGenerationRecord(
                    id=generation_id,
                    user_id=subject.user_id,
                    subject_key=subject.key,
                    user_kind=subject.kind,
                    vehicle_id=vehicle_id,
                    type="cockpit_theme",
                    user_prompt=user_prompt,
                    enhanced_prompt=enhanced_prompt,
                    prompt_hash=prompt_hash,
                    provider=provider,
                    model=model,
                    image_provider=image_provider,
                    image_model=image_model,
                    status=status,
                    latency_ms=latency_ms,
                    cost_est_cny=cost_est_cny,
                    image_cost_est_cny=image_cost_est_cny,
                    output_url=wallpaper_url,
                    cached=cached,
                    regenerated=regenerated,
                    degraded_reason=degraded_reason,
                    metadata_json=metadata,
                )
            )
            await self._session.flush()
            self._session.add(
                CockpitThemeRecord(
                    id=theme_id,
                    generation_id=generation_id,
                    user_id=subject.user_id,
                    subject_key=subject.key,
                    vehicle_id=vehicle_id,
                    name=spec.name,
                    theme_spec_json=spec.model_dump(mode="json"),
                    wallpaper_url=wallpaper_url,
                    prompt_hash=prompt_hash,
                )
            )
        return StoredTheme(
            theme_id, generation_id, spec, wallpaper_url, subject.key, prompt_hash, vehicle_id
        )

    async def get_theme(self, theme_id: UUID, subject: UsageSubject) -> StoredTheme | None:
        async with self._session.begin():
            record = await self._session.scalar(
                select(CockpitThemeRecord).where(
                    CockpitThemeRecord.id == theme_id,
                    CockpitThemeRecord.subject_key == subject.key,
                )
            )
        return self._to_stored(record) if record else None

    async def mark_applied(self, theme_id: UUID) -> None:
        async with self._session.begin():
            await self._session.execute(
                update(CockpitThemeRecord)
                .where(CockpitThemeRecord.id == theme_id)
                .values(
                    applied_count=CockpitThemeRecord.applied_count + 1,
                    last_applied_at=func.now(),
                    updated_at=func.now(),
                )
            )

    async def metrics(self) -> dict[str, float | int]:
        async with self._session.begin():
            row = (
                await self._session.execute(
                    select(
                        func.count(AigcGenerationRecord.id),
                        func.sum(
                            case(
                                (
                                    AigcGenerationRecord.status.in_(
                                        ["success", "degraded", "cached"]
                                    ),
                                    1,
                                ),
                                else_=0,
                            )
                        ),
                        func.avg(AigcGenerationRecord.latency_ms),
                        func.sum(AigcGenerationRecord.cost_est_cny),
                        func.sum(case((AigcGenerationRecord.regenerated.is_(True), 1), else_=0)),
                    )
                )
            ).one()
            applied = await self._session.scalar(select(func.sum(CockpitThemeRecord.applied_count)))
        total, success, average_latency, cost, regenerated = row
        total = int(total or 0)
        return {
            "generation_count": total,
            "generation_success_rate": float(success or 0) / total if total else 0,
            "average_latency_ms": float(average_latency or 0),
            "cost_est_cny": float(cost or 0),
            "apply_rate": float(applied or 0) / total if total else 0,
            "regeneration_rate": float(regenerated or 0) / total if total else 0,
        }

    @staticmethod
    def _to_stored(record: CockpitThemeRecord) -> StoredTheme:
        return StoredTheme(
            record.id,
            record.generation_id,
            ThemeSpec.model_validate(record.theme_spec_json),
            record.wallpaper_url,
            record.subject_key,
            record.prompt_hash,
            record.vehicle_id,
        )
