from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from apps.api.aigc.repository import UsageSubject
from apps.api.api.dependencies import (
    get_external_vehicle_data_service,
    get_garage_service,
    get_registered_identity,
    get_usage_subject,
)
from apps.api.auth.service import AuthIdentity
from apps.api.core.errors import AppError
from apps.api.product.schemas import (
    RecallListResponse,
    VinDecodeRequest,
    VinDecodeResponse,
)
from apps.api.product.service import (
    ExternalVehicleDataService,
    GarageService,
    ProductNotFoundError,
)

router = APIRouter()


@router.post("/vin/decode", response_model=VinDecodeResponse)
async def decode_vin(
    payload: VinDecodeRequest,
    _: Annotated[AuthIdentity, Depends(get_registered_identity)],
    service: Annotated[ExternalVehicleDataService, Depends(get_external_vehicle_data_service)],
) -> VinDecodeResponse:
    try:
        return await service.decode_vin(payload.vin, payload.model_year)
    except ValueError as exc:
        raise AppError("INVALID_VIN", str(exc), status_code=422) from exc


@router.get("/recalls", response_model=RecallListResponse)
async def get_recalls(
    request: Request,
    subject: Annotated[UsageSubject, Depends(get_usage_subject)],
    service: Annotated[ExternalVehicleDataService, Depends(get_external_vehicle_data_service)],
    garage: Annotated[GarageService, Depends(get_garage_service)],
    vehicle_id: Annotated[UUID | None, Query()] = None,
) -> RecallListResponse:
    try:
        resolved = vehicle_id
        if resolved is None:
            primary = await garage.primary(
                user_id=subject.user_id,
                demo_vehicle_id=request.app.state.settings.default_vehicle_id,
            )
            resolved = primary.id
        return await service.recalls(vehicle_id=resolved, user_id=subject.user_id)
    except ProductNotFoundError as exc:
        raise AppError("VEHICLE_NOT_FOUND", "Vehicle was not found", status_code=404) from exc
