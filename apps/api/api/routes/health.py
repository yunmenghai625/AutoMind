from datetime import UTC, datetime

from fastapi import APIRouter, Request

from apps.api.infrastructure.database import check_database
from apps.api.schemas.health import DependencyHealth, HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    database = await check_database(settings)
    if not settings.rate_limit_enabled:
        redis = DependencyHealth(status="disabled", detail="Rate limiting is disabled")
    elif not request.app.state.rate_limiter.configured:
        redis = DependencyHealth(status="unavailable", detail="Redis is not configured")
    else:
        redis_ok = await request.app.state.rate_limiter.health()
        redis = DependencyHealth(
            status="ok" if redis_ok else "unavailable",
            detail=None if redis_ok else "Redis ping failed",
        )

    if not settings.otel_enabled:
        telemetry = DependencyHealth(status="disabled", detail="OTLP export is disabled")
    elif not settings.otel_exporter_otlp_endpoint:
        telemetry = DependencyHealth(status="unavailable", detail="OTLP endpoint is missing")
    else:
        telemetry = DependencyHealth(status="ok", detail="OTLP exporters are configured")

    aigc_s3_required = settings.aigc_asset_storage == "s3"
    diagnosis_s3_required = settings.diagnosis_asset_storage == "s3"
    s3_required = aigc_s3_required or diagnosis_s3_required
    required_buckets_configured = (
        not aigc_s3_required or bool(settings.aigc_r2_bucket or settings.r2_bucket)
    ) and (not diagnosis_s3_required or bool(settings.diagnosis_r2_bucket or settings.r2_bucket))
    storage_configured = bool(
        settings.r2_endpoint
        and required_buckets_configured
        and settings.r2_access_key
        and settings.r2_secret_key
    )
    if not s3_required:
        storage = DependencyHealth(status="disabled", detail="Local asset storage")
    elif storage_configured:
        storage = DependencyHealth(status="ok", detail="S3-compatible storage is configured")
    else:
        storage = DependencyHealth(status="unavailable", detail="S3 configuration is incomplete")

    dependencies = {
        "database": DependencyHealth(**database.model_dump()),
        "redis": redis,
        "storage": storage,
        "telemetry": telemetry,
    }
    critical_statuses = [database.status, redis.status, storage.status]
    status = "ok" if "unavailable" not in critical_statuses else "degraded"
    return HealthResponse(
        status=status,
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        timestamp=datetime.now(UTC),
        dependencies=dependencies,
    )
