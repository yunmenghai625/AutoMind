import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from apps.api.aigc.repository import UsageSubject
from apps.api.product.repository import (
    ExternalDataRepository,
    FeedbackRepository,
    GarageRepository,
    PreferenceRepository,
    UsageQuotaRepository,
)
from apps.api.product.schemas import (
    FeedbackRequest,
    FeedbackView,
    GarageVehicleView,
    PreferenceResponse,
    PreferenceValues,
    RecallListResponse,
    RecallView,
    VehicleCreateRequest,
    VehicleUpdateRequest,
    VehicleView,
    VinDecodeResponse,
)
from apps.api.product.vehicle_data import VehicleDataProvider, VehicleDataProviderError


class ProductNotFoundError(LookupError):
    pass


class ProductAuthenticationRequiredError(PermissionError):
    pass


class UsageQuotaExceededError(RuntimeError):
    pass


class PreferenceService:
    def __init__(self, repository: PreferenceRepository) -> None:
        self._repository = repository

    async def get(self, user_id: UUID) -> PreferenceResponse:
        record = await self._repository.get(user_id)
        if record is None:
            values = PreferenceValues()
            return PreferenceResponse(
                user_id=user_id,
                updated_at=datetime.now(UTC),
                **values.model_dump(),
            )
        return _preference_view(record)

    async def update(self, user_id: UUID, values: PreferenceValues) -> PreferenceResponse:
        return _preference_view(await self._repository.upsert(user_id, values))

    async def delete(self, user_id: UUID) -> bool:
        return await self._repository.delete(user_id)


class GarageService:
    def __init__(self, repository: GarageRepository, *, vin_secret: str) -> None:
        self._repository = repository
        self._vin_secret = vin_secret.encode()

    async def list(self, user_id: UUID) -> list[VehicleView]:
        return [_vehicle_view(*row) for row in await self._repository.list(user_id)]

    async def get(self, vehicle_id: UUID, user_id: UUID) -> VehicleView:
        row = await self._repository.get(vehicle_id, user_id)
        if row is None:
            raise ProductNotFoundError
        return _vehicle_view(*row)

    async def primary(self, *, user_id: UUID | None, demo_vehicle_id: UUID) -> GarageVehicleView:
        row = (
            await self._repository.first(user_id)
            if user_id is not None
            else await self._repository.get(demo_vehicle_id, None)
        )
        if row is None:
            raise ProductNotFoundError
        vehicle, state = row
        view = _vehicle_view(vehicle, state)
        return GarageVehicleView(
            **view.model_dump(),
            name=f"{vehicle.make} {vehicle.model}",
            vin=view.vin_masked or "Not provided",
            lastCheck=vehicle.updated_at.date().isoformat(),
            batteryHealth=None,
            trim=vehicle.powertrain,
            color="Not specified",
        )

    async def resolve_vehicle_id(
        self,
        *,
        user_id: UUID | None,
        requested_vehicle_id: UUID | None,
        demo_vehicle_id: UUID,
    ) -> UUID:
        if user_id is None:
            resolved = requested_vehicle_id or demo_vehicle_id
            if resolved != demo_vehicle_id:
                raise ProductNotFoundError
            return resolved
        elif requested_vehicle_id is not None:
            resolved = requested_vehicle_id
            row = await self._repository.get(resolved, user_id)
        else:
            row = await self._repository.first(user_id)
            resolved = row[0].id if row else demo_vehicle_id
        if row is None:
            raise ProductNotFoundError
        return resolved

    async def create(self, user_id: UUID, values: VehicleCreateRequest) -> VehicleView:
        vin_hash, vin_last4 = self._vin_values(values.vin)
        return _vehicle_view(
            *(
                await self._repository.create(
                    user_id=user_id,
                    values=values,
                    vin_hash=vin_hash,
                    vin_last4=vin_last4,
                )
            )
        )

    async def update(
        self, vehicle_id: UUID, user_id: UUID, values: VehicleUpdateRequest
    ) -> VehicleView:
        vin_supplied = "vin" in values.model_fields_set
        vin_hash, vin_last4 = self._vin_values(values.vin) if vin_supplied else (None, None)
        row = await self._repository.update(
            vehicle_id=vehicle_id,
            user_id=user_id,
            values=values,
            vin_hash=vin_hash,
            vin_last4=vin_last4,
            vin_supplied=vin_supplied,
        )
        if row is None:
            raise ProductNotFoundError
        return _vehicle_view(*row)

    async def delete(self, vehicle_id: UUID, user_id: UUID) -> None:
        if not await self._repository.delete(vehicle_id, user_id):
            raise ProductNotFoundError

    def _vin_values(self, vin: str | None) -> tuple[str | None, str | None]:
        if vin is None:
            return None, None
        normalized = normalize_vin(vin)
        digest = hmac.new(self._vin_secret, normalized.encode(), hashlib.sha256).hexdigest()
        return digest, normalized[-4:]


class ExternalVehicleDataService:
    def __init__(
        self,
        *,
        repository: ExternalDataRepository,
        garage: GarageRepository,
        provider: VehicleDataProvider,
        cache_ttl_hours: int,
        vin_secret: str,
    ) -> None:
        self._repository = repository
        self._garage = garage
        self._provider = provider
        self._ttl = timedelta(hours=cache_ttl_hours)
        self._vin_secret = vin_secret.encode()

    async def decode_vin(self, vin: str, model_year: int | None) -> VinDecodeResponse:
        normalized_vin = normalize_vin(vin)
        key = (
            "vin:" + hmac.new(self._vin_secret, normalized_vin.encode(), hashlib.sha256).hexdigest()
        )
        cached = await self._repository.get_cache(key)
        now = datetime.now(UTC)
        masked = _masked_vin(normalized_vin[-4:]) or "not retained"
        if cached and cached.expires_at > now:
            return _vin_response(
                masked,
                cached.normalized_json,
                cached.source,
                "cached",
                True,
                cached.fetched_at,
            )
        try:
            decoded = await self._provider.decode_vin(normalized_vin, model_year)
            record = await self._repository.save_cache(
                cache_key=key,
                data_type="vin_decode",
                normalized=decoded,
                source=self._provider.name,
                status="success",
                error_code=None,
                fetched_at=now,
                expires_at=now + self._ttl,
            )
            return _vin_response(
                masked, decoded, record.source, "success", False, record.fetched_at
            )
        except VehicleDataProviderError as exc:
            if cached:
                return _vin_response(
                    masked,
                    cached.normalized_json,
                    cached.source,
                    "degraded",
                    True,
                    cached.fetched_at,
                    type(exc).__name__,
                )
            return _vin_response(
                masked,
                {},
                self._provider.name,
                "unavailable",
                False,
                None,
                type(exc).__name__,
            )

    async def recalls(self, *, vehicle_id: UUID, user_id: UUID | None) -> RecallListResponse:
        row = await self._garage.get(vehicle_id, user_id)
        if row is None:
            raise ProductNotFoundError
        vehicle, _ = row
        raw_key = f"{vehicle.id}|{vehicle.make}|{vehicle.model}|{vehicle.year}".lower().encode()
        key = "recalls:" + hashlib.sha256(raw_key).hexdigest()
        cached = await self._repository.get_cache(key)
        now = datetime.now(UTC)
        if cached and cached.expires_at > now:
            return await self._recall_response(vehicle_id, "cached", True, cached.fetched_at)
        try:
            recalls = await self._provider.recalls(
                make=vehicle.make, model=vehicle.model, year=vehicle.year
            )
            expires = now + self._ttl
            await self._repository.replace_recalls(
                vehicle_id=vehicle_id,
                recalls=recalls,
                fetched_at=now,
                expires_at=expires,
            )
            cache = await self._repository.save_cache(
                cache_key=key,
                data_type="recalls",
                normalized={"count": len(recalls)},
                source=self._provider.name,
                status="success",
                error_code=None,
                fetched_at=now,
                expires_at=expires,
                vehicle_id=vehicle_id,
            )
            return await self._recall_response(vehicle_id, "success", False, cache.fetched_at)
        except VehicleDataProviderError as exc:
            records = await self._repository.recalls(vehicle_id)
            if cached or records:
                fetched = cached.fetched_at if cached else records[0].fetched_at
                return await self._recall_response(
                    vehicle_id,
                    "degraded",
                    True,
                    fetched,
                    type(exc).__name__,
                )
            return RecallListResponse(
                vehicle_id=vehicle_id,
                recalls=[],
                status="unavailable",
                cached=False,
                fetched_at=None,
                error_code=type(exc).__name__,
            )

    async def _recall_response(
        self,
        vehicle_id: UUID,
        status: str,
        cached: bool,
        fetched_at: datetime,
        error_code: str | None = None,
    ) -> RecallListResponse:
        records = await self._repository.recalls(vehicle_id)
        return RecallListResponse(
            vehicle_id=vehicle_id,
            recalls=[
                RecallView(
                    id=item.external_id,
                    component=item.component,
                    summary=item.summary,
                    risk=item.risk,
                    issuedAt=item.issued_at,
                    recommendedAction=item.recommended_action,
                    source=item.source,
                )
                for item in records
            ],
            status=status,
            cached=cached,
            fetched_at=fetched_at,
            error_code=error_code,
        )


class FeedbackService:
    def __init__(self, repository: FeedbackRepository) -> None:
        self._repository = repository

    async def save(self, subject: UsageSubject, values: FeedbackRequest) -> FeedbackView:
        record = await self._repository.save(subject, values)
        if record is None:
            raise ProductNotFoundError
        return _feedback_view(record)

    async def list(self, subject: UsageSubject) -> list[FeedbackView]:
        return [_feedback_view(item) for item in await self._repository.list(subject)]


class UsageQuotaService:
    def __init__(self, repository: UsageQuotaRepository, *, enabled: bool) -> None:
        self._repository = repository
        self._enabled = enabled

    async def reserve_text(self, subject: UsageSubject, limit: int) -> int:
        if not self._enabled:
            return 0
        used = await self._repository.reserve_text(subject, limit)
        if used is None:
            raise UsageQuotaExceededError
        return used


def normalize_vin(vin: str) -> str:
    normalized = vin.strip().upper()
    if len(normalized) != 17 or any(char in normalized for char in "IOQ"):
        raise ValueError("VIN must contain 17 valid characters and cannot include I, O or Q")
    if not normalized.isalnum():
        raise ValueError("VIN contains invalid characters")
    return normalized


def _masked_vin(last4: str | None) -> str | None:
    return f"*************{last4}" if last4 else None


def _vehicle_view(vehicle: Any, state: Any) -> VehicleView:
    return VehicleView(
        id=vehicle.id,
        make=vehicle.make,
        model=vehicle.model,
        year=vehicle.year,
        powertrain=vehicle.powertrain,
        mileageKm=vehicle.mileage_km,
        vinMasked=_masked_vin(vehicle.vin_last4),
        batterySoc=state.battery_soc if state else None,
        updatedAt=vehicle.updated_at,
    )


def _preference_view(record: Any) -> PreferenceResponse:
    return PreferenceResponse(
        user_id=record.user_id,
        preferredTemperature=record.preferred_temp_c,
        seatHeatingLevel=record.seat_heat_level,
        preferredChargingLimit=record.charge_limit_percent,
        preferredDrivingMode=record.driving_mode,
        extensions=record.preferences_json,
        updated_at=record.updated_at,
    )


def _vin_response(
    masked_vin: str,
    values: dict[str, Any],
    source: str,
    status: str,
    cached: bool,
    fetched_at: datetime | None,
    error_code: str | None = None,
) -> VinDecodeResponse:
    return VinDecodeResponse(
        vin_masked=masked_vin,
        make=values.get("make"),
        model=values.get("model"),
        model_year=values.get("model_year"),
        vehicle_type=values.get("vehicle_type"),
        fuel_type=values.get("fuel_type"),
        source=source,
        status=status,
        cached=cached,
        fetched_at=fetched_at,
        error_code=error_code,
    )


def _feedback_view(record: Any) -> FeedbackView:
    return FeedbackView(
        id=record.id,
        run_id=record.run_id,
        message_id=record.message_id,
        rating=record.rating,
        reason=record.reason,
        comment=record.comment,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )
