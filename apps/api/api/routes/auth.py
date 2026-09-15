from typing import Annotated

from fastapi import APIRouter, Depends, Request

from apps.api.api.dependencies import get_auth_identity
from apps.api.auth.schemas import AdminLoginRequest, AdminLoginResponse
from apps.api.auth.service import (
    AdminAuthenticationError,
    AuthIdentity,
    create_admin_session,
)
from apps.api.core.errors import AppError
from apps.api.product.schemas import UserView

router = APIRouter()


@router.post("/admin/login", response_model=AdminLoginResponse)
async def login_admin(payload: AdminLoginRequest, request: Request) -> AdminLoginResponse:
    settings = request.app.state.settings
    password_hash = (
        settings.admin_password_hash.get_secret_value() if settings.admin_password_hash else ""
    )
    jwt_secret = settings.jwt_secret.get_secret_value() if settings.jwt_secret else ""
    if not password_hash:
        raise AppError(
            "ADMIN_LOGIN_NOT_CONFIGURED",
            "管理员登录尚未配置",
            status_code=503,
        )
    try:
        token, expires_at, identity = create_admin_session(
            submitted_username=payload.username,
            submitted_password=payload.password,
            configured_username=settings.admin_username,
            configured_password_hash=password_hash,
            jwt_secret=jwt_secret,
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            lifetime_hours=settings.admin_session_hours,
        )
    except AdminAuthenticationError as exc:
        raise AppError(
            "ADMIN_LOGIN_FAILED",
            "管理员账号或密码错误",
            status_code=401,
        ) from exc
    return AdminLoginResponse(
        accessToken=token,
        expiresAt=expires_at,
        user=UserView(
            kind="registered",
            user_id=identity.user_id,
            email=identity.email,
            role=identity.role,
        ),
    )


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
