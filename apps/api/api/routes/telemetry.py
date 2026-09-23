import logging
from typing import Literal

from fastapi import APIRouter, Response, status
from pydantic import BaseModel, Field

from apps.api.core.telemetry import record_operation

router = APIRouter()
logger = logging.getLogger(__name__)
_KNOWN_ERROR_NAMES = {
    "AbortError",
    "Error",
    "NetworkError",
    "RangeError",
    "ReferenceError",
    "SyntaxError",
    "TypeError",
    "UnhandledRejection",
}


class FrontendErrorEvent(BaseModel):
    source: Literal["window.error", "unhandledrejection", "react"]
    name: str = Field(min_length=1, max_length=80)
    route: str = Field(min_length=1, max_length=200)
    digest: str | None = Field(default=None, max_length=128)


class FrontendWebVitalEvent(BaseModel):
    name: Literal["CLS", "FCP", "INP", "LCP", "TTFB"]
    value: float = Field(ge=0, le=10_000_000)
    rating: Literal["good", "needs-improvement", "poor"]
    route: str = Field(min_length=1, max_length=200)


@router.post("/frontend-errors", status_code=status.HTTP_202_ACCEPTED)
async def report_frontend_error(payload: FrontendErrorEvent) -> Response:
    error_name = payload.name if payload.name in _KNOWN_ERROR_NAMES else "OtherError"
    logger.warning(
        "Frontend error observed",
        extra={
            "frontend_source": payload.source,
            "error_name": error_name,
            "route": payload.route,
            "error_digest": payload.digest,
        },
    )
    record_operation(
        "frontend",
        status="failed",
        latency_ms=0,
        name=f"{payload.source}:{error_name}",
    )
    return Response(status_code=status.HTTP_202_ACCEPTED)


@router.post("/web-vitals", status_code=status.HTTP_202_ACCEPTED)
async def report_web_vital(payload: FrontendWebVitalEvent) -> Response:
    metric_status = {
        "good": "success",
        "needs-improvement": "degraded",
        "poor": "failed",
    }[payload.rating]
    logger.info(
        "Frontend Web Vital observed",
        extra={
            "metric_name": payload.name,
            "metric_value": payload.value,
            "metric_rating": payload.rating,
            "route": payload.route,
        },
    )
    record_operation(
        "frontend.web_vital",
        status=metric_status,
        latency_ms=payload.value,
        name=payload.name,
    )
    return Response(status_code=status.HTTP_202_ACCEPTED)
