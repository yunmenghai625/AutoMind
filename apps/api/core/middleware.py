import asyncio
import hashlib
import logging
import re
import secrets
import time
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from apps.api.core.request_context import (
    request_id_context,
    run_id_context,
    trace_id_context,
    traffic_class_context,
)
from apps.api.core.telemetry import current_trace_id, record_operation, span
from apps.api.infrastructure.database import get_session_factory
from apps.api.operations.repository import OperationalRepository

logger = logging.getLogger(__name__)
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


class RequestContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        supplied = request.headers.get("X-Request-ID", "")
        request_id = supplied if REQUEST_ID_PATTERN.fullmatch(supplied) else str(uuid4())
        request.state.request_id = request_id
        request_token = request_id_context.set(request_id)
        run_token = run_id_context.set(None)
        traffic_class = _traffic_class(request)
        request.state.traffic_class = traffic_class
        traffic_token = traffic_class_context.set(traffic_class)
        started = time.perf_counter()
        response: Response | None = None

        with span(
            f"{request.method} {request.url.path}",
            {"http.request.method": request.method, "url.path": request.url.path},
        ) as request_span:
            trace_id = current_trace_id() or uuid4().hex
            trace_token = trace_id_context.set(trace_id)
            request.state.trace_id = trace_id
            try:
                response = await self._rate_limit(request)
                if response is None:
                    try:
                        async with asyncio.timeout(
                            request.app.state.settings.request_timeout_seconds
                        ):
                            response = await call_next(request)
                    except TimeoutError:
                        request.state.error_code = "REQUEST_TIMEOUT"
                        response = _error_response(
                            request_id,
                            504,
                            "REQUEST_TIMEOUT",
                            "Request exceeded the global timeout",
                        )
            finally:
                duration_ms = round((time.perf_counter() - started) * 1000, 2)
                status_code = response.status_code if response is not None else 500
                error_code = getattr(request.state, "error_code", None)
                route = request.scope.get("route")
                route_path = getattr(route, "path", request.url.path)
                request_span.update_name(f"{request.method} {route_path}")
                request_span.set_attribute("http.route", route_path)
                logger.info(
                    "HTTP request completed",
                    extra={
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": status_code,
                        "duration_ms": duration_ms,
                        "trace_id": trace_id,
                        "run_id": run_id_context.get(),
                        "error_code": error_code,
                        "traffic_class": traffic_class,
                    },
                )
                record_operation(
                    "http",
                    status=(
                        "success"
                        if status_code < 400
                        else "client_error"
                        if status_code < 500
                        else "server_error"
                    ),
                    latency_ms=duration_ms,
                    name=f"{request.method} {route_path}",
                )
                await self._persist(request, status_code, duration_ms, error_code)
                trace_id_context.reset(trace_token)
                request_id_context.reset(request_token)
                run_id_context.reset(run_token)
                traffic_class_context.reset(traffic_token)

        if response is None:
            raise RuntimeError("Request completed without a response")
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Trace-ID"] = trace_id
        limit = getattr(request.state, "rate_limit", None)
        if limit is not None:
            response.headers["X-RateLimit-Limit"] = str(limit.limit)
            response.headers["X-RateLimit-Remaining"] = str(limit.remaining)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        if request.app.state.settings.app_env == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    async def _rate_limit(self, request: Request) -> Response | None:
        settings = request.app.state.settings
        if not settings.rate_limit_enabled or request.url.path.endswith("/health"):
            return None
        login_path = f"{settings.api_v1_prefix}/auth/admin/login"
        limiter = (
            request.app.state.admin_login_limiter
            if request.url.path == login_path
            else request.app.state.rate_limiter
        )
        identity = (
            request.headers.get("Authorization")
            or request.headers.get("X-Guest-ID")
            or (request.client.host if request.client else "unknown")
        )
        key = hashlib.sha256(identity.encode()).hexdigest()
        decision = await limiter.allow(key)
        request.state.rate_limit = decision
        if decision.allowed:
            return None
        request.state.error_code = "RATE_LIMIT_EXCEEDED"
        response = _error_response(
            request.state.request_id,
            429,
            "RATE_LIMIT_EXCEEDED",
            "Too many requests",
        )
        response.headers["Retry-After"] = str(decision.retry_after_seconds)
        return response

    async def _persist(
        self,
        request: Request,
        status_code: int,
        duration_ms: float,
        error_code: str | None,
    ) -> None:
        settings = request.app.state.settings
        if not settings.operational_metrics_persistence_enabled:
            return
        try:
            async with asyncio.timeout(settings.operational_metrics_timeout_seconds):
                async with get_session_factory(settings)() as session:
                    await OperationalRepository(session).record_http(
                        request_id=request.state.request_id,
                        trace_id=request.state.trace_id,
                        method=request.method,
                        path=request.url.path,
                        status_code=status_code,
                        duration_ms=duration_ms,
                        error_code=error_code,
                        traffic_class=request.state.traffic_class,
                    )
        except Exception as exc:
            logger.warning(
                "Operational HTTP metric persistence failed",
                extra={"error_type": type(exc).__name__},
            )


def _error_response(request_id: str, status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "error": {"code": code, "message": message, "details": None},
            "request_id": request_id,
        },
    )


def _traffic_class(request: Request) -> str:
    if request.headers.get("X-AutoMind-Traffic-Class") != "load_test":
        return "user"
    configured = request.app.state.settings.load_test_token
    expected = configured.get_secret_value() if configured else ""
    supplied = request.headers.get("X-Load-Test-Token", "")
    return "load_test" if expected and secrets.compare_digest(supplied, expected) else "user"
