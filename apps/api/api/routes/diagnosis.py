from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import FileResponse

from apps.api.aigc.repository import UsageSubject
from apps.api.api.dependencies import (
    enforce_ai_admission,
    get_budget_guard,
    get_diagnosis_service,
    get_garage_service,
    get_usage_subject,
)
from apps.api.core.errors import AppError
from apps.api.diagnosis.image_guard import ImageGuardError
from apps.api.diagnosis.schemas import DiagnosisResponse
from apps.api.diagnosis.service import (
    DiagnosisInput,
    DiagnosisQuotaExceededError,
    DiagnosisService,
)
from apps.api.operations.service import BudgetGuard
from apps.api.product.service import GarageService, ProductNotFoundError

router = APIRouter()


@router.post("", response_model=DiagnosisResponse)
async def diagnose_image(
    request: Request,
    file: Annotated[UploadFile, File(description="Dashboard or warning-light image")],
    _admission: Annotated[None, Depends(enforce_ai_admission)],
    subject: Annotated[UsageSubject, Depends(get_usage_subject)],
    service: Annotated[DiagnosisService, Depends(get_diagnosis_service)],
    garage: Annotated[GarageService, Depends(get_garage_service)],
    budget: Annotated[BudgetGuard, Depends(get_budget_guard)],
    description: Annotated[str | None, Form(max_length=1000)] = None,
) -> DiagnosisResponse:
    max_bytes = request.app.state.settings.image_upload_max_bytes
    content = await file.read(max_bytes + 1)
    try:
        vehicle_id = await garage.resolve_vehicle_id(
            user_id=subject.vehicle_user_id,
            requested_vehicle_id=None,
            demo_vehicle_id=request.app.state.settings.default_vehicle_id,
        )
        budget_state = await budget.current()
        return await service.diagnose(
            request_id=request.state.request_id,
            subject=subject,
            vehicle_id=vehicle_id,
            payload=DiagnosisInput(
                content=content,
                declared_mime=file.content_type,
                filename=file.filename or "dashboard-image",
                context=description,
            ),
            economy_mode=budget_state.state != "normal",
        )
    except ProductNotFoundError as exc:
        raise AppError("VEHICLE_NOT_FOUND", "Vehicle was not found", status_code=404) from exc
    except ImageGuardError as exc:
        raise AppError(exc.code, str(exc), status_code=422) from exc
    except DiagnosisQuotaExceededError as exc:
        raise AppError(
            "DIAGNOSIS_DAILY_QUOTA_EXCEEDED",
            "今日图片诊断次数已用完，请明日再试。",
            status_code=429,
        ) from exc


@router.get("/assets/{filename}", include_in_schema=False)
async def get_diagnosis_asset(filename: str, request: Request) -> FileResponse:
    safe_name = Path(filename).name
    root = Path(request.app.state.settings.diagnosis_local_asset_dir).resolve()
    target = (root / safe_name).resolve()
    if target.parent != root or not target.is_file():
        raise AppError("ASSET_NOT_FOUND", "Diagnosis image was not found", status_code=404)
    return FileResponse(target, media_type="image/jpeg")
