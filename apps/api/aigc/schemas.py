from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ThemeSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=80)
    ambient_color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    ambient_brightness: int = Field(ge=0, le=100)
    display_mode: Literal["comfort", "night", "minimal", "focus"]
    music_style: str = Field(min_length=1, max_length=80)
    temperature: float = Field(ge=16, le=30)
    wallpaper_prompt: str = Field(min_length=10, max_length=1000)

    @field_validator("name", "music_style", "wallpaper_prompt")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("value must not be blank")
        return normalized


class GenerateThemeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(min_length=2, max_length=500)
    vehicle_id: UUID | None = None
    regenerate: bool = False


class ApplyThemeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirmed: Literal[True]
    expected_version: int = Field(ge=0)


class ThemeMetadata(BaseModel):
    generation_id: UUID
    provider: str
    model: str
    image_provider: str | None
    image_model: str | None
    latency_ms: int
    cost_est_cny: float
    image_cost_est_cny: float
    status: str
    cached: bool
    degraded_reason: str | None = None
    quota_used: int
    quota_limit: int
    budget_state: Literal["normal", "economy", "exhausted"]


class ThemeResponse(BaseModel):
    request_id: str
    theme_id: UUID
    theme_spec: ThemeSpec
    wallpaper_url: str | None
    metadata: ThemeMetadata


class ThemeApplyResponse(BaseModel):
    request_id: str
    theme_id: UUID
    applied: bool
    theme_spec: ThemeSpec
    wallpaper_url: str | None
    vehicle_state_version: int
    agent_run_id: UUID
