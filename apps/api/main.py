from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.api.router import api_router
from apps.api.api.routes import health
from apps.api.core.ai_admission import AiAdmissionController
from apps.api.core.config import Settings, get_settings
from apps.api.core.errors import install_exception_handlers
from apps.api.core.logging import configure_logging
from apps.api.core.middleware import RequestContextMiddleware
from apps.api.core.rate_limit import RedisRateLimiter
from apps.api.core.telemetry import configure_telemetry, shutdown_telemetry
from apps.api.infrastructure.database import close_database


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings.log_level)
    configure_telemetry(resolved_settings)

    redis_url = (
        resolved_settings.redis_url.get_secret_value() if resolved_settings.redis_url else ""
    )
    redis_scope = (
        f"test-{uuid4().hex}" if resolved_settings.app_env == "test" else resolved_settings.app_env
    )
    rate_limiter = RedisRateLimiter(
        url=redis_url,
        limit=resolved_settings.rate_limit_per_minute,
        timeout_seconds=resolved_settings.redis_timeout_seconds,
        namespace=f"{redis_scope}:http",
    )
    admin_login_limiter = RedisRateLimiter(
        url=redis_url,
        limit=resolved_settings.admin_login_rate_limit_per_minute,
        timeout_seconds=resolved_settings.redis_timeout_seconds,
        namespace=f"{redis_scope}:admin-login",
    )
    ai_rate_limiter = RedisRateLimiter(
        url=redis_url,
        limit=resolved_settings.ai_rate_limit_per_minute,
        timeout_seconds=resolved_settings.redis_timeout_seconds,
        namespace=f"{redis_scope}:ai",
    )
    ai_admission = AiAdmissionController(
        url=redis_url,
        limit=resolved_settings.ai_max_concurrency,
        lease_seconds=resolved_settings.ai_lease_seconds,
        timeout_seconds=resolved_settings.redis_timeout_seconds,
        fail_closed=resolved_settings.app_env in {"staging", "production"},
        namespace=redis_scope,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await rate_limiter.close()
        await admin_login_limiter.close()
        await ai_rate_limiter.close()
        await ai_admission.close()
        await close_database()
        shutdown_telemetry()

    application = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        docs_url="/docs" if resolved_settings.docs_enabled else None,
        redoc_url=None,
        lifespan=lifespan,
    )
    application.state.settings = resolved_settings
    application.state.rate_limiter = rate_limiter
    application.state.admin_login_limiter = admin_login_limiter
    application.state.ai_rate_limiter = ai_rate_limiter
    application.state.ai_admission = ai_admission
    application.add_middleware(RequestContextMiddleware)

    if resolved_settings.cors_origin_list:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=resolved_settings.cors_origin_list,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=[
                "Authorization",
                "Content-Type",
                "X-Request-ID",
                "X-Guest-ID",
                "X-AutoMind-Traffic-Class",
                "X-Load-Test-Token",
            ],
            expose_headers=[
                "X-Request-ID",
                "X-Trace-ID",
                "X-RateLimit-Limit",
                "X-RateLimit-Remaining",
            ],
        )

    install_exception_handlers(application)
    application.include_router(api_router, prefix=resolved_settings.api_v1_prefix)
    application.include_router(health.router, include_in_schema=False)
    return application


app = create_app()
