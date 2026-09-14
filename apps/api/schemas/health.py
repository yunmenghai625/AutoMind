from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class DependencyHealth(BaseModel):
    status: Literal["ok", "unavailable", "disabled"]
    detail: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    service: str
    version: str
    environment: str
    timestamp: datetime
    dependencies: dict[str, DependencyHealth]
