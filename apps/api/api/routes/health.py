from datetime import UTC, datetime

from fastapi import APIRouter, Request

from apps.api.infrastructure.database import check_database
from apps.api.schemas.health import DependencyHealth, HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    database = await check_database(settings)
    status = "ok" if database.status in {"ok", "disabled"} else "degraded"
    return HealthResponse(
        status=status,
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        timestamp=datetime.now(UTC),
        dependencies={"database": DependencyHealth(**database.model_dump())},
    )
