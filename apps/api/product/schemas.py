from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class UserView(BaseModel):
    kind: Literal["guest", "registered"]
    user_id: UUID | None = None
    email: str | None = None
    role: str


class PreferenceValues(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    preferred_temp_c: float = Field(default=23, ge=16, le=30, alias="preferredTemperature")
    seat_heat_level: int = Field(default=1, ge=0, le=3, alias="seatHeatingLevel")
    charge_limit_percent: int = Field(default=80, ge=50, le=100, alias="preferredChargingLimit")
    driving_mode: Literal["Comfort", "Sport", "Eco"] = Field(
        default="Comfort", alias="preferredDrivingMode"
    )
    extensions: dict[str, Any] = Field(default_factory=dict)

    @field_validator("extensions")
    @classmethod
    def limit_extensions(cls, value: dict[str, Any]) -> dict[str, Any]:
        if len(value) > 20:
            raise ValueError("extensions contains too many keys")
        if len(str(value)) > 4000:
            raise ValueError("extensions is too large")
        return value


class PreferenceResponse(PreferenceValues):
    user_id: UUID
    updated_at: datetime


class VehicleCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    make: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=80)
    year: int = Field(ge=1886, le=2100)
    powertrain: Literal["ICE", "HEV", "PHEV", "BEV", "FCEV"]
    mileage_km: float = Field(default=0, ge=0, le=5_000_000)
    vin: str | None = Field(default=None, min_length=17, max_length=17)


class VehicleUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    make: str | None = Field(default=None, min_length=1, max_length=80)
    model: str | None = Field(default=None, min_length=1, max_length=80)
    year: int | None = Field(default=None, ge=1886, le=2100)
    powertrain: Literal["ICE", "HEV", "PHEV", "BEV", "FCEV"] | None = None
    mileage_km: float | None = Field(default=None, ge=0, le=5_000_000)
    vin: str | None = Field(default=None, min_length=17, max_length=17)


class VehicleView(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    make: str
    model: str
    year: int
    powertrain: str
    mileage_km: float = Field(alias="mileageKm")
    vin_masked: str | None = Field(alias="vinMasked")
    battery_soc: float | None = Field(alias="batterySoc")
    updated_at: datetime = Field(alias="updatedAt")


class GarageVehicleView(VehicleView):
    name: str
    vin: str
    last_check: str = Field(alias="lastCheck")
    battery_health: float | None = Field(default=None, alias="batteryHealth")
    trim: str
    color: str


class VinDecodeRequest(BaseModel):
    vin: str = Field(min_length=17, max_length=17)
    model_year: int | None = Field(default=None, ge=1886, le=2100)


class VinDecodeResponse(BaseModel):
    vin_masked: str
    make: str | None
    model: str | None
    model_year: int | None
    vehicle_type: str | None
    fuel_type: str | None
    source: str
    status: Literal["success", "cached", "degraded", "unavailable"]
    cached: bool
    fetched_at: datetime | None
    error_code: str | None = None


class RecallView(BaseModel):
    id: str
    component: str
    summary: str
    risk: Literal["Low", "Medium", "High"]
    issued_at: datetime | None = Field(alias="issuedAt")
    recommended_action: str = Field(alias="recommendedAction")
    source: str


class RecallListResponse(BaseModel):
    vehicle_id: UUID
    recalls: list[RecallView]
    status: Literal["success", "cached", "degraded", "unavailable"]
    cached: bool
    fetched_at: datetime | None
    error_code: str | None = None


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: UUID | None = None
    message_id: UUID | None = None
    rating: Literal[-1, 1]
    reason: str | None = Field(default=None, max_length=80)
    comment: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def target_required(self) -> "FeedbackRequest":
        if self.run_id is None and self.message_id is None:
            raise ValueError("run_id or message_id is required")
        return self


class FeedbackView(FeedbackRequest):
    id: UUID
    created_at: datetime
    updated_at: datetime
