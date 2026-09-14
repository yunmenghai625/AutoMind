from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse

from apps.api.aigc.repository import AigcRepository, UsageSubject
from apps.api.aigc.schemas import (
    ApplyThemeRequest,
    GenerateThemeRequest,
    ThemeApplyResponse,
    ThemeResponse,
)
from apps.api.aigc.service import (
    AigcQuotaExceededError,
    ThemeApplyService,
    ThemeGenerationService,
    ThemeNotFoundError,
)
from apps.api.aigc.theme_generator import InvalidThemeSpecError
from apps.api.api.dependencies import (
    get_aigc_repository,
    get_budget_guard,
    get_garage_service,
    get_theme_apply_service,
    get_theme_generation_service,
    get_usage_subject,
)
from apps.api.core.errors import AppError
from apps.api.domain.vehicle.exceptions import (
    VehicleNotFoundError,
    VehicleStorageError,
    VehicleValidationError,
    VehicleVersionConflictError,
)
from apps.api.operations.service import BudgetGuard
from apps.api.product.service import GarageService, ProductNotFoundError

router = APIRouter()


@router.post("/themes", response_model=ThemeResponse)
async def generate_theme(
    payload: GenerateThemeRequest,
    request: Request,
    subject: Annotated[UsageSubject, Depends(get_usage_subject)],
    service: Annotated[ThemeGenerationService, Depends(get_theme_generation_service)],
    garage: Annotated[GarageService, Depends(get_garage_service)],
    budget: Annotated[BudgetGuard, Depends(get_budget_guard)],
) -> ThemeResponse:
    try:
        budget_state = await budget.current()
        vehicle_id = await garage.resolve_vehicle_id(
            user_id=subject.user_id,
            requested_vehicle_id=payload.vehicle_id,
            demo_vehicle_id=request.app.state.settings.default_vehicle_id,
        )
        result = await service.generate(
            subject=subject,
            vehicle_id=vehicle_id,
            prompt=payload.prompt,
            regenerate=payload.regenerate,
            request_id=request.state.request_id,
            economy_mode=budget_state.state != "normal",
        )
    except ProductNotFoundError as exc:
        raise AppError("VEHICLE_NOT_FOUND", "Vehicle was not found", status_code=404) from exc
    except AigcQuotaExceededError as exc:
        raise AppError(
            "AIGC_DAILY_QUOTA_EXCEEDED",
            "今日主题生成次数已用完，请明日再试。",
            status_code=429,
        ) from exc
    except InvalidThemeSpecError as exc:
        raise AppError("INVALID_THEME_SPEC", "模型未返回有效的座舱主题。", status_code=422) from exc
    return ThemeResponse(
        request_id=request.state.request_id,
        theme_id=result.theme.id,
        theme_spec=result.theme.spec,
        wallpaper_url=result.theme.wallpaper_url,
        metadata=result.metadata,
    )


@router.post("/themes/{theme_id}/apply", response_model=ThemeApplyResponse)
async def apply_theme(
    theme_id: UUID,
    payload: ApplyThemeRequest,
    request: Request,
    subject: Annotated[UsageSubject, Depends(get_usage_subject)],
    service: Annotated[ThemeApplyService, Depends(get_theme_apply_service)],
) -> ThemeApplyResponse:
    try:
        result = await service.apply(
            theme_id=theme_id,
            subject=subject,
            vehicle_id=None,
            expected_version=payload.expected_version,
            request_id=request.state.request_id,
        )
    except ThemeNotFoundError as exc:
        raise AppError("THEME_NOT_FOUND", "Theme was not found", status_code=404) from exc
    except VehicleVersionConflictError as exc:
        raise AppError(
            "VEHICLE_VERSION_CONFLICT",
            "Vehicle state was updated by another request",
            status_code=409,
            details={
                "expected_version": exc.expected_version,
                "current_version": exc.current_version,
            },
        ) from exc
    except VehicleNotFoundError as exc:
        raise AppError("VEHICLE_NOT_FOUND", "Vehicle was not found", status_code=404) from exc
    except (VehicleValidationError, ValueError) as exc:
        raise AppError("THEME_APPLY_INVALID", str(exc), status_code=422) from exc
    except VehicleStorageError as exc:
        raise AppError("VEHICLE_STORAGE_UNAVAILABLE", str(exc), status_code=503) from exc
    except PermissionError as exc:
        raise AppError("THEME_APPLY_REJECTED", str(exc), status_code=409) from exc
    return ThemeApplyResponse(
        request_id=request.state.request_id,
        theme_id=result.theme.id,
        applied=True,
        theme_spec=result.theme.spec,
        wallpaper_url=result.theme.wallpaper_url,
        vehicle_state_version=result.vehicle_state_version,
        agent_run_id=result.agent_run_id,
    )


@router.get("/metrics")
async def get_aigc_metrics(
    repository: Annotated[AigcRepository, Depends(get_aigc_repository)],
) -> dict[str, float | int]:
    return await repository.metrics()


@router.get("/assets/{filename}", include_in_schema=False)
async def get_generated_asset(filename: str, request: Request) -> FileResponse:
    safe_name = Path(filename).name
    root = Path(request.app.state.settings.aigc_local_asset_dir).resolve()
    target = (root / safe_name).resolve()
    if target.parent != root or not target.is_file():
        raise AppError("ASSET_NOT_FOUND", "Generated asset was not found", status_code=404)
    return FileResponse(target)
