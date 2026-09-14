from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.aigc.repository import UsageSubject
from apps.api.infrastructure.models import (
    AgentRunRecord,
    FeedbackRecord,
    UsageDailyRecord,
    UserPreferenceRecord,
    UserRecord,
    VehicleDataCacheRecord,
    VehicleRecallRecord,
    VehicleRecord,
    VehicleStateRecord,
)
from apps.api.product.schemas import (
    FeedbackRequest,
    PreferenceValues,
    VehicleCreateRequest,
    VehicleUpdateRequest,
)


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def ensure(self, *, user_id: UUID, email: str | None, role: str) -> UserRecord:
        statement = insert(UserRecord).values(
            id=user_id,
            email=email,
            role=role,
            status="active",
        )
        statement = statement.on_conflict_do_update(
            index_elements=[UserRecord.id],
            set_={
                "email": func.coalesce(statement.excluded.email, UserRecord.email),
                "role": statement.excluded.role,
                "updated_at": func.now(),
            },
        ).returning(UserRecord)
        async with self._session.begin():
            return (await self._session.execute(statement)).scalar_one()


class PreferenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: UUID) -> UserPreferenceRecord | None:
        async with self._session.begin():
            return await self._session.scalar(
                select(UserPreferenceRecord).where(UserPreferenceRecord.user_id == user_id)
            )

    async def upsert(self, user_id: UUID, values: PreferenceValues) -> UserPreferenceRecord:
        statement = insert(UserPreferenceRecord).values(
            user_id=user_id,
            preferred_temp_c=values.preferred_temp_c,
            seat_heat_level=values.seat_heat_level,
            charge_limit_percent=values.charge_limit_percent,
            driving_mode=values.driving_mode,
            preferences_json=values.extensions,
        )
        statement = statement.on_conflict_do_update(
            index_elements=[UserPreferenceRecord.user_id],
            set_={
                "preferred_temp_c": statement.excluded.preferred_temp_c,
                "seat_heat_level": statement.excluded.seat_heat_level,
                "charge_limit_percent": statement.excluded.charge_limit_percent,
                "driving_mode": statement.excluded.driving_mode,
                "preferences_json": statement.excluded.preferences_json,
                "updated_at": func.now(),
            },
        ).returning(UserPreferenceRecord)
        async with self._session.begin():
            return (await self._session.execute(statement)).scalar_one()

    async def delete(self, user_id: UUID) -> bool:
        async with self._session.begin():
            result = await self._session.execute(
                delete(UserPreferenceRecord).where(UserPreferenceRecord.user_id == user_id)
            )
        return bool(result.rowcount)


class GarageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self, user_id: UUID) -> list[tuple[VehicleRecord, VehicleStateRecord | None]]:
        async with self._session.begin():
            rows = await self._session.execute(
                select(VehicleRecord, VehicleStateRecord)
                .outerjoin(VehicleStateRecord, VehicleStateRecord.vehicle_id == VehicleRecord.id)
                .where(VehicleRecord.user_id == user_id)
                .order_by(VehicleRecord.created_at.asc())
            )
        return list(rows.tuples())

    async def get(
        self, vehicle_id: UUID, user_id: UUID | None
    ) -> tuple[VehicleRecord, VehicleStateRecord | None] | None:
        filters = [VehicleRecord.id == vehicle_id]
        filters.append(
            VehicleRecord.user_id == user_id
            if user_id is not None
            else VehicleRecord.user_id.is_(None)
        )
        async with self._session.begin():
            row = (
                await self._session.execute(
                    select(VehicleRecord, VehicleStateRecord)
                    .outerjoin(
                        VehicleStateRecord, VehicleStateRecord.vehicle_id == VehicleRecord.id
                    )
                    .where(*filters)
                )
            ).first()
        return row._t if row else None

    async def first(self, user_id: UUID) -> tuple[VehicleRecord, VehicleStateRecord | None] | None:
        rows = await self.list(user_id)
        return rows[0] if rows else None

    async def create(
        self,
        *,
        user_id: UUID,
        values: VehicleCreateRequest,
        vin_hash: str | None,
        vin_last4: str | None,
    ) -> tuple[VehicleRecord, VehicleStateRecord]:
        vehicle = VehicleRecord(
            id=uuid4(),
            user_id=user_id,
            make=values.make.strip(),
            model=values.model.strip(),
            year=values.year,
            powertrain=values.powertrain,
            vin_hash=vin_hash,
            vin_last4=vin_last4,
            mileage_km=values.mileage_km,
        )
        state = VehicleStateRecord(
            vehicle_id=vehicle.id,
            speed_kph=0,
            gear="P",
            battery_soc=0,
            range_km=0,
            climate_json={"driver": 22, "passenger": 22},
            seat_heat_json={"driver": 0, "passenger": 0},
            window_position_json={"driver": 0, "passenger": 0},
            door_state_json={"driver": "CLOSED", "passenger": "CLOSED"},
            light_state="OFF",
            charge_status="IDLE",
            version=0,
        )
        async with self._session.begin():
            self._session.add_all([vehicle, state])
        return vehicle, state

    async def update(
        self,
        *,
        vehicle_id: UUID,
        user_id: UUID,
        values: VehicleUpdateRequest,
        vin_hash: str | None,
        vin_last4: str | None,
        vin_supplied: bool,
    ) -> tuple[VehicleRecord, VehicleStateRecord | None] | None:
        changes = values.model_dump(exclude_unset=True, exclude={"vin"})
        if vin_supplied:
            changes.update(vin_hash=vin_hash, vin_last4=vin_last4)
        changes["updated_at"] = func.now()
        async with self._session.begin():
            result = await self._session.execute(
                update(VehicleRecord)
                .where(VehicleRecord.id == vehicle_id, VehicleRecord.user_id == user_id)
                .values(**changes)
                .returning(VehicleRecord.id)
            )
            found = result.scalar_one_or_none()
        return await self.get(found, user_id) if found else None

    async def delete(self, vehicle_id: UUID, user_id: UUID) -> bool:
        async with self._session.begin():
            result = await self._session.execute(
                delete(VehicleRecord).where(
                    VehicleRecord.id == vehicle_id, VehicleRecord.user_id == user_id
                )
            )
        return bool(result.rowcount)


class ExternalDataRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_cache(self, cache_key: str) -> VehicleDataCacheRecord | None:
        async with self._session.begin():
            return await self._session.scalar(
                select(VehicleDataCacheRecord).where(VehicleDataCacheRecord.cache_key == cache_key)
            )

    async def save_cache(
        self,
        *,
        cache_key: str,
        data_type: str,
        normalized: dict[str, Any],
        source: str,
        status: str,
        error_code: str | None,
        fetched_at: datetime,
        expires_at: datetime,
        vehicle_id: UUID | None = None,
    ) -> VehicleDataCacheRecord:
        statement = insert(VehicleDataCacheRecord).values(
            id=uuid4(),
            vehicle_id=vehicle_id,
            cache_key=cache_key,
            data_type=data_type,
            normalized_json=normalized,
            source=source,
            status=status,
            error_code=error_code,
            fetched_at=fetched_at,
            expires_at=expires_at,
        )
        statement = statement.on_conflict_do_update(
            index_elements=[VehicleDataCacheRecord.cache_key],
            set_={
                "vehicle_id": statement.excluded.vehicle_id,
                "normalized_json": statement.excluded.normalized_json,
                "source": statement.excluded.source,
                "status": statement.excluded.status,
                "error_code": statement.excluded.error_code,
                "fetched_at": statement.excluded.fetched_at,
                "expires_at": statement.excluded.expires_at,
                "updated_at": func.now(),
            },
        ).returning(VehicleDataCacheRecord)
        async with self._session.begin():
            return (await self._session.execute(statement)).scalar_one()

    async def replace_recalls(
        self,
        *,
        vehicle_id: UUID,
        recalls: list[dict[str, Any]],
        fetched_at: datetime,
        expires_at: datetime,
    ) -> None:
        async with self._session.begin():
            await self._session.execute(
                delete(VehicleRecallRecord).where(VehicleRecallRecord.vehicle_id == vehicle_id)
            )
            self._session.add_all(
                [
                    VehicleRecallRecord(
                        id=uuid4(),
                        vehicle_id=vehicle_id,
                        fetched_at=fetched_at,
                        expires_at=expires_at,
                        **item,
                    )
                    for item in recalls
                ]
            )

    async def recalls(self, vehicle_id: UUID) -> list[VehicleRecallRecord]:
        async with self._session.begin():
            return list(
                (
                    await self._session.scalars(
                        select(VehicleRecallRecord)
                        .where(VehicleRecallRecord.vehicle_id == vehicle_id)
                        .order_by(VehicleRecallRecord.issued_at.desc().nullslast())
                    )
                ).all()
            )


class FeedbackRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, subject: UsageSubject, values: FeedbackRequest) -> FeedbackRecord | None:
        if values.run_id is not None:
            async with self._session.begin():
                exists = await self._session.scalar(
                    select(AgentRunRecord.id).where(AgentRunRecord.id == values.run_id)
                )
            if exists is None:
                return None
        conflict_column = "run_id" if values.run_id else "message_id"
        statement = insert(FeedbackRecord).values(
            id=uuid4(),
            user_id=subject.user_id,
            subject_key=subject.key,
            run_id=values.run_id,
            message_id=values.message_id,
            rating=values.rating,
            reason=values.reason,
            comment=values.comment,
        )
        statement = statement.on_conflict_do_update(
            index_elements=[FeedbackRecord.subject_key, getattr(FeedbackRecord, conflict_column)],
            set_={
                "rating": statement.excluded.rating,
                "reason": statement.excluded.reason,
                "comment": statement.excluded.comment,
                "updated_at": func.now(),
            },
        ).returning(FeedbackRecord)
        async with self._session.begin():
            return (await self._session.execute(statement)).scalar_one()

    async def list(self, subject: UsageSubject) -> list[FeedbackRecord]:
        async with self._session.begin():
            return list(
                (
                    await self._session.scalars(
                        select(FeedbackRecord)
                        .where(FeedbackRecord.subject_key == subject.key)
                        .order_by(FeedbackRecord.created_at.desc())
                        .limit(100)
                    )
                ).all()
            )


class UsageQuotaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def reserve_text(self, subject: UsageSubject, limit: int) -> int | None:
        statement = insert(UsageDailyRecord).values(
            date=date.today(),
            subject_key=subject.key,
            user_id=subject.user_id,
            user_kind=subject.kind,
            requests=1,
            text_requests=1,
            aigc_requests=0,
            tokens=0,
            image_calls=0,
            diagnosis_requests=0,
            cost_est_cny=0,
        )
        statement = statement.on_conflict_do_update(
            index_elements=[UsageDailyRecord.date, UsageDailyRecord.subject_key],
            set_={
                "requests": UsageDailyRecord.requests + 1,
                "text_requests": UsageDailyRecord.text_requests + 1,
                "updated_at": func.now(),
            },
            where=UsageDailyRecord.text_requests < limit,
        ).returning(UsageDailyRecord.text_requests)
        async with self._session.begin():
            used = (await self._session.execute(statement)).scalar_one_or_none()
        return int(used) if used is not None else None

    async def today(self, subject: UsageSubject) -> UsageDailyRecord | None:
        async with self._session.begin():
            return await self._session.scalar(
                select(UsageDailyRecord).where(
                    UsageDailyRecord.date == date.today(),
                    UsageDailyRecord.subject_key == subject.key,
                )
            )


def utcnow() -> datetime:
    return datetime.now(UTC)
