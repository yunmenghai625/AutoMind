from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

WarningType = Literal[
    "tire_pressure",
    "brake_system",
    "check_engine",
    "battery",
    "oil_pressure",
    "airbag",
    "abs",
    "temperature",
    "unknown",
]
RiskLevel = Literal["Information", "Warning", "Critical"]


class WarningDetection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    warning_type: WarningType
    warning_code: str | None = Field(default=None, max_length=40)
    label: str = Field(min_length=1, max_length=120)
    confidence: float = Field(ge=0, le=1)
    visible_evidence: list[str] = Field(min_length=1, max_length=5)
    uncertainty: str = Field(min_length=1, max_length=500)


class VlmStructuredOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detections: list[WarningDetection] = Field(min_length=1, max_length=4)


class DiagnosisCitation(BaseModel):
    source: str
    chapter: str | None = None
    page: int | None = None
    snippet: str


class DiagnosisCause(BaseModel):
    title: str
    detail: str


class DiagnosisRecommendation(BaseModel):
    title: str
    detail: str


class DetectedWarningResponse(BaseModel):
    code: str
    label: str
    confidence: int
    risk: Literal["Low", "Medium", "High"]


class DiagnosisMetadata(BaseModel):
    diagnosis_id: UUID
    run_id: UUID
    provider: str
    model: str
    latency_ms: int
    cost_est_cny: float
    status: str
    low_confidence: bool
    quota_used: int
    quota_limit: int
    image_expires_at: datetime


class DiagnosisResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    request_id: str
    detected: list[DetectedWarningResponse]
    causes: list[DiagnosisCause]
    recommendations: list[DiagnosisRecommendation]
    references: list[DiagnosisCitation]
    pipeline: list[str]
    processed_at: datetime = Field(alias="processedAt")
    message: str
    metadata: DiagnosisMetadata
