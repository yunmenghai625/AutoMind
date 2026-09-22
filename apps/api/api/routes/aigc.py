from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, Response

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
from apps.api.aigc.storage import (
    S3ThemeAssetStore,
    ThemeAssetNotFoundError,
    ThemeAssetStoreError,
)
from apps.api.aigc.theme_generator import InvalidThemeSpecError
from apps.api.api.dependencies import (
    enforce_ai_admission,
    get_admin_identity,
    get_aigc_repository,
    get_budget_guard,
    get_garage_service,
    get_theme_apply_service,
    get_theme_generation_service,
    get_usage_subject,
)
from apps.api.auth.service import AuthIdentity
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
    _admission: Annotated[None, Depends(enforce_ai_admission)],
    subject: Annotated[UsageSubject, Depends(get_usage_subject)],
    service: Annotated[ThemeGenerationService, Depends(get_theme_generation_service)],
    garage: Annotated[GarageService, Depends(get_garage_service)],
    budget: Annotated[BudgetGuard, Depends(get_budget_guard)],
) -> ThemeResponse:
    try:
        budget_state = await budget.current()
        vehicle_id = await garage.resolve_vehicle_id(
            user_id=subject.vehicle_user_id,
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
    _admin: Annotated[AuthIdentity, Depends(get_admin_identity)],
    repository: Annotated[AigcRepository, Depends(get_aigc_repository)],
) -> dict[str, float | int]:
    return await repository.metrics()


@router.get("/assets/{filename}", include_in_schema=False)
async def get_generated_asset(filename: str, request: Request) -> Response:
    safe_name = Path(filename).name
    settings = request.app.state.settings
    if settings.aigc_asset_storage == "s3":
        store = S3ThemeAssetStore(
            endpoint=settings.r2_endpoint,
            bucket=settings.aigc_r2_bucket or settings.r2_bucket,
            access_key=settings.r2_access_key.get_secret_value() if settings.r2_access_key else "",
            secret_key=(
                settings.r2_secret_key.get_secret_value() if settings.r2_secret_key else ""
            ),
            public_base_url=None,
            prefix=settings.aigc_storage_prefix,
            proxy_base_url=f"{settings.api_v1_prefix}/aigc/assets",
        )
        try:
            content, content_type = await store.get(safe_name)
        except ThemeAssetNotFoundError as exc:
            raise AppError(
                "ASSET_NOT_FOUND", "Generated asset was not found", status_code=404
            ) from exc
        except ThemeAssetStoreError as exc:
            raise AppError(
                "ASSET_STORAGE_UNAVAILABLE",
                "Asset storage is unavailable",
                status_code=503,
            ) from exc
        return Response(
            content=content,
            media_type=content_type,
            headers={"Cache-Control": "public, max-age=86400"},
        )
    root = Path(settings.aigc_local_asset_dir).resolve()
    target = (root / safe_name).resolve()
    if target.parent != root or not target.is_file():
        raise AppError("ASSET_NOT_FOUND", "Generated asset was not found", status_code=404)
    return FileResponse(target)
