from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from apps.api.aigc.repository import UsageSubject
from apps.api.api.dependencies import get_garage_service, get_usage_subject, get_vehicle_service
from apps.api.core.errors import AppError
from apps.api.domain.vehicle.entities import VehicleStateChange as VehicleStateChangeData
from apps.api.domain.vehicle.entities import VehicleStateData
from apps.api.domain.vehicle.exceptions import (
    VehicleNotFoundError,
    VehicleStorageError,
    VehicleValidationError,
    VehicleVersionConflictError,
)
from apps.api.domain.vehicle.service import VehicleService
from apps.api.product.service import GarageService, ProductNotFoundError
from apps.api.schemas.common import ErrorResponse
from apps.api.schemas.vehicle import (
    ClimateState,
    VehicleControlRequest,
    VehicleControlResponse,
    VehicleState,
    VehicleStateChange,
    VehicleStateResponse,
    ZonedDoorState,
    ZonedPercentageState,
    ZonedSeatHeatState,
)

router = APIRouter()


@router.get(
    "/state",
    response_model=VehicleStateResponse,
    responses={404: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
async def get_vehicle_state(
    request: Request,
    service: Annotated[VehicleService, Depends(get_vehicle_service)],
    subject: Annotated[UsageSubject, Depends(get_usage_subject)],
    garage: Annotated[GarageService, Depends(get_garage_service)],
    vehicle_id: Annotated[UUID | None, Query()] = None,
) -> VehicleStateResponse:
    try:
        resolved_vehicle_id = await garage.resolve_vehicle_id(
            user_id=subject.vehicle_user_id,
            requested_vehicle_id=vehicle_id,
            demo_vehicle_id=request.app.state.settings.default_vehicle_id,
        )
        state = await service.get_state(resolved_vehicle_id)
    except ProductNotFoundError as exc:
        raise AppError("VEHICLE_NOT_FOUND", "Vehicle was not found", status_code=404) from exc
    except (VehicleNotFoundError, VehicleStorageError) as exc:
        raise _to_api_error(exc) from exc
    return VehicleStateResponse(
        request_id=request.state.request_id,
        source="live",
        state=_state_response(state),
    )


@router.post(
    "/control",
    response_model=VehicleControlResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def control_vehicle(
    payload: VehicleControlRequest,
    request: Request,
    service: Annotated[VehicleService, Depends(get_vehicle_service)],
    subject: Annotated[UsageSubject, Depends(get_usage_subject)],
    garage: Annotated[GarageService, Depends(get_garage_service)],
) -> VehicleControlResponse:
    try:
        vehicle_id = await garage.resolve_vehicle_id(
            user_id=subject.vehicle_user_id,
            requested_vehicle_id=payload.vehicle_id,
            demo_vehicle_id=request.app.state.settings.default_vehicle_id,
        )
        change = await service.set_property(
            vehicle_id,
            payload.property,
            payload.zone,
            payload.value,
            expected_version=payload.expected_version,
            request_id=request.state.request_id,
        )
    except ProductNotFoundError as exc:
        raise AppError("VEHICLE_NOT_FOUND", "Vehicle was not found", status_code=404) from exc
    except (
        VehicleNotFoundError,
        VehicleStorageError,
        VehicleValidationError,
        VehicleVersionConflictError,
    ) as exc:
        raise _to_api_error(exc) from exc

    return VehicleControlResponse(
        request_id=request.state.request_id,
        source="live",
        change=_change_response(change),
        state=_state_response(change.state),
    )


def _state_response(state: VehicleStateData) -> VehicleState:
    return VehicleState(
        vehicle_id=state.vehicle_id,
        speed_kph=state.speed_kph,
        gear=state.gear,
        battery_soc=state.battery_soc,
        range_km=state.range_km,
        climate=ClimateState(
            driver_temp_c=state.climate["driver"],
            passenger_temp_c=state.climate["passenger"],
        ),
        seat_heat=ZonedSeatHeatState(**state.seat_heat),
        window_position=ZonedPercentageState(**state.window_position),
        door_state=ZonedDoorState(**state.door_state),
        light_state=state.light_state,
        charge_status=state.charge_status,
        version=state.version,
        updated_at=state.updated_at,
    )


def _change_response(change: VehicleStateChangeData) -> VehicleStateChange:
    return VehicleStateChange(
        property=change.property_name,
        zone=change.zone,
        old_value=change.old_value,
        new_value=change.new_value,
    )


def _to_api_error(exc: Exception) -> AppError:
    if isinstance(exc, VehicleNotFoundError):
        return AppError(
            "VEHICLE_NOT_FOUND",
            "Vehicle was not found",
            status_code=404,
            details={"vehicle_id": str(exc.vehicle_id)},
        )
    if isinstance(exc, VehicleVersionConflictError):
        return AppError(
            "VEHICLE_VERSION_CONFLICT",
            "Vehicle state was updated by another request",
            status_code=409,
            details={
                "expected_version": exc.expected_version,
                "current_version": exc.current_version,
            },
        )
    if isinstance(exc, VehicleValidationError):
        return AppError(exc.code, exc.message, status_code=422)
    if isinstance(exc, VehicleStorageError):
        return AppError(
            "VEHICLE_STORAGE_UNAVAILABLE",
            "Vehicle state is temporarily unavailable",
            status_code=503,
        )
    return AppError("INTERNAL_ERROR", "An unexpected error occurred", status_code=500)
