from time import perf_counter
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from apps.api.api.dependencies import (
    get_admin_identity,
    get_admin_metrics_service,
    get_agent_trace_store,
    get_budget_guard,
    get_operational_repository,
)
from apps.api.core.errors import AppError
from apps.api.infrastructure.agent_trace import PostgresAgentTraceStore
from apps.api.infrastructure.database import check_database
from apps.api.operations.repository import OperationalRepository
from apps.api.operations.service import AdminMetricsService, BudgetGuard

router = APIRouter(dependencies=[Depends(get_admin_identity)])


@router.get("/overview")
async def get_overview(
    repository: Annotated[OperationalRepository, Depends(get_operational_repository)],
) -> dict[str, Any]:
    return await repository.overview()


@router.get("/metrics")
async def get_metrics(
    service: Annotated[AdminMetricsService, Depends(get_admin_metrics_service)],
    days: Annotated[int, Query(ge=1, le=30)] = 14,
) -> dict[str, Any]:
    return await service.metrics(days)


@router.get("/operational-metrics")
async def get_operational_metrics(
    repository: Annotated[OperationalRepository, Depends(get_operational_repository)],
) -> dict[str, Any]:
    return await repository.operational_totals()


@router.get("/budget")
async def get_budget(
    guard: Annotated[BudgetGuard, Depends(get_budget_guard)],
) -> dict[str, Any]:
    return await guard.as_dict()


@router.get("/components")
async def get_components(request: Request) -> list[dict[str, Any]]:
    started = perf_counter()
    database = await check_database(request.app.state.settings)
    database_latency = round((perf_counter() - started) * 1000, 2)
    redis_started = perf_counter()
    redis_ok = await request.app.state.rate_limiter.health()
    redis_latency = round((perf_counter() - redis_started) * 1000, 2)
    return [
        {
            "name": "API",
            "status": "operational",
            "latencyMs": 0,
            "detail": f"AutoMind API {request.app.state.settings.app_version}",
        },
        {
            "name": "Database",
            "status": "operational" if database.status == "ok" else "degraded",
            "latencyMs": database_latency,
            "detail": f"PostgreSQL {database.status}",
        },
        {
            "name": "Rate Limiter",
            "status": "operational" if redis_ok else "degraded",
            "latencyMs": redis_latency,
            "detail": request.app.state.rate_limiter.backend,
        },
        {
            "name": "Telemetry",
            "status": "operational" if request.app.state.settings.otel_enabled else "degraded",
            "latencyMs": 0,
            "detail": "OTLP enabled"
            if request.app.state.settings.otel_enabled
            else "OTLP disabled",
        },
    ]


@router.get("/safety-events")
async def get_safety_events(
    repository: Annotated[OperationalRepository, Depends(get_operational_repository)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[dict[str, Any]]:
    return await repository.safety_events(limit)


@router.get("/requests/{request_id}")
async def get_request(
    request_id: str,
    repository: Annotated[OperationalRepository, Depends(get_operational_repository)],
) -> dict[str, Any]:
    result = await repository.request_by_id(request_id)
    if result is None:
        raise AppError("REQUEST_NOT_FOUND", "Request metric was not found", status_code=404)
    return result


@router.get("/agent-runs")
async def list_agent_runs(
    store: Annotated[PostgresAgentTraceStore, Depends(get_agent_trace_store)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[dict[str, Any]]:
    return await store.list_runs(limit=limit)


@router.get("/agent-runs/{run_id}")
async def get_agent_run(
    run_id: UUID,
    store: Annotated[PostgresAgentTraceStore, Depends(get_agent_trace_store)],
) -> dict[str, Any]:
    result = await store.get_run(run_id)
    if result is None:
        raise AppError("AGENT_RUN_NOT_FOUND", "Agent 运行记录不存在", status_code=404)
    return result
