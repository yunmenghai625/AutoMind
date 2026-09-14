from collections.abc import Awaitable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from apps.api.aigc.repository import UsageSubject
from apps.api.api.dependencies import (
    get_garage_service,
    get_registered_identity,
    get_usage_subject,
)
from apps.api.auth.service import AuthIdentity
from apps.api.core.errors import AppError
from apps.api.product.schemas import (
    GarageVehicleView,
    VehicleCreateRequest,
    VehicleUpdateRequest,
    VehicleView,
)
from apps.api.product.service import GarageService, ProductNotFoundError

router = APIRouter()


@router.get("/vehicle", response_model=GarageVehicleView)
async def get_primary_vehicle(
    request: Request,
    subject: Annotated[UsageSubject, Depends(get_usage_subject)],
    service: Annotated[GarageService, Depends(get_garage_service)],
) -> GarageVehicleView:
    try:
        return await service.primary(
            user_id=subject.user_id,
            demo_vehicle_id=request.app.state.settings.default_vehicle_id,
        )
    except ProductNotFoundError as exc:
        raise AppError("VEHICLE_NOT_FOUND", "Vehicle was not found", status_code=404) from exc


@router.get("/vehicles", response_model=list[VehicleView])
async def list_vehicles(
    identity: Annotated[AuthIdentity, Depends(get_registered_identity)],
    service: Annotated[GarageService, Depends(get_garage_service)],
) -> list[VehicleView]:
    assert identity.user_id is not None
    return await service.list(identity.user_id)


@router.post("/vehicles", response_model=VehicleView, status_code=status.HTTP_201_CREATED)
async def create_vehicle(
    payload: VehicleCreateRequest,
    identity: Annotated[AuthIdentity, Depends(get_registered_identity)],
    service: Annotated[GarageService, Depends(get_garage_service)],
) -> VehicleView:
    assert identity.user_id is not None
    try:
        return await service.create(identity.user_id, payload)
    except ValueError as exc:
        raise AppError("INVALID_VIN", str(exc), status_code=422) from exc


@router.get("/vehicles/{vehicle_id}", response_model=VehicleView)
async def get_vehicle(
    vehicle_id: UUID,
    identity: Annotated[AuthIdentity, Depends(get_registered_identity)],
    service: Annotated[GarageService, Depends(get_garage_service)],
) -> VehicleView:
    assert identity.user_id is not None
    return await _owned_vehicle(service.get(vehicle_id, identity.user_id))


@router.patch("/vehicles/{vehicle_id}", response_model=VehicleView)
async def update_vehicle(
    vehicle_id: UUID,
    payload: VehicleUpdateRequest,
    identity: Annotated[AuthIdentity, Depends(get_registered_identity)],
    service: Annotated[GarageService, Depends(get_garage_service)],
) -> VehicleView:
    assert identity.user_id is not None
    try:
        return await _owned_vehicle(service.update(vehicle_id, identity.user_id, payload))
    except ValueError as exc:
        raise AppError("INVALID_VIN", str(exc), status_code=422) from exc


@router.delete("/vehicles/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vehicle(
    vehicle_id: UUID,
    identity: Annotated[AuthIdentity, Depends(get_registered_identity)],
    service: Annotated[GarageService, Depends(get_garage_service)],
) -> None:
    assert identity.user_id is not None
    try:
        await service.delete(vehicle_id, identity.user_id)
    except ProductNotFoundError as exc:
        raise AppError("VEHICLE_NOT_FOUND", "Vehicle was not found", status_code=404) from exc


async def _owned_vehicle(awaitable: Awaitable[VehicleView]) -> VehicleView:
    try:
        return await awaitable
    except ProductNotFoundError as exc:
        raise AppError("VEHICLE_NOT_FOUND", "Vehicle was not found", status_code=404) from exc
