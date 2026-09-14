from typing import Annotated

from fastapi import APIRouter, Depends

from apps.api.api.dependencies import get_auth_identity
from apps.api.auth.service import AuthIdentity
from apps.api.product.schemas import UserView

router = APIRouter()


@router.get("/me", response_model=UserView)
async def get_current_identity(
    identity: Annotated[AuthIdentity, Depends(get_auth_identity)],
) -> UserView:
    return UserView(
        kind="registered" if identity.is_registered else "guest",
        user_id=identity.user_id,
        email=identity.email,
        role=identity.role,
    )
