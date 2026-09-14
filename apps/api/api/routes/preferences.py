from typing import Annotated

from fastapi import APIRouter, Depends

from apps.api.api.dependencies import get_preference_service, get_registered_identity
from apps.api.auth.service import AuthIdentity
from apps.api.product.schemas import PreferenceResponse, PreferenceValues
from apps.api.product.service import PreferenceService

router = APIRouter()


@router.get("", response_model=PreferenceResponse)
async def get_preferences(
    identity: Annotated[AuthIdentity, Depends(get_registered_identity)],
    service: Annotated[PreferenceService, Depends(get_preference_service)],
) -> PreferenceResponse:
    assert identity.user_id is not None
    return await service.get(identity.user_id)


@router.put("", response_model=PreferenceResponse)
async def update_preferences(
    payload: PreferenceValues,
    identity: Annotated[AuthIdentity, Depends(get_registered_identity)],
    service: Annotated[PreferenceService, Depends(get_preference_service)],
) -> PreferenceResponse:
    assert identity.user_id is not None
    return await service.update(identity.user_id, payload)


@router.delete("")
async def delete_preferences(
    identity: Annotated[AuthIdentity, Depends(get_registered_identity)],
    service: Annotated[PreferenceService, Depends(get_preference_service)],
) -> dict[str, bool]:
    assert identity.user_id is not None
    return {"deleted": await service.delete(identity.user_id)}
