import json
from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from apps.api.agents.service import AgentResult, CockpitAgentService
from apps.api.aigc.repository import UsageSubject
from apps.api.api.dependencies import (
    get_cockpit_agent_service,
    get_garage_service,
    get_usage_quota_service,
    get_usage_subject,
)
from apps.api.core.errors import AppError
from apps.api.product.service import (
    GarageService,
    ProductNotFoundError,
    UsageQuotaExceededError,
    UsageQuotaService,
)
from apps.api.schemas.chat import (
    ChatMessage,
    ChatMessageMeta,
    CockpitVehicleState,
    SendChatRequest,
    SendChatResponse,
    ToolCallView,
)

router = APIRouter()


@router.post("", response_model=SendChatResponse)
async def send_chat(
    payload: SendChatRequest,
    request: Request,
    service: Annotated[CockpitAgentService, Depends(get_cockpit_agent_service)],
    subject: Annotated[UsageSubject, Depends(get_usage_subject)],
    quota: Annotated[UsageQuotaService, Depends(get_usage_quota_service)],
    garage: Annotated[GarageService, Depends(get_garage_service)],
) -> SendChatResponse:
    await _reserve_quota(request, subject, quota)
    vehicle_id = await _resolve_vehicle(request, subject, garage)
    result = await _run(service, request, payload.message, payload.sessionId, vehicle_id)
    return _to_response(result)


@router.get("/stream")
async def stream_chat(
    request: Request,
    service: Annotated[CockpitAgentService, Depends(get_cockpit_agent_service)],
    subject: Annotated[UsageSubject, Depends(get_usage_subject)],
    quota: Annotated[UsageQuotaService, Depends(get_usage_quota_service)],
    garage: Annotated[GarageService, Depends(get_garage_service)],
    message: Annotated[str, Query(min_length=1, max_length=2000)],
    session_id: Annotated[str | None, Query()] = None,
) -> StreamingResponse:
    await _reserve_quota(request, subject, quota)
    vehicle_id = await _resolve_vehicle(request, subject, garage)

    async def event_stream() -> Any:
        yield _sse("started", {"requestId": request.state.request_id})
        result = await _run(service, request, message, session_id, vehicle_id)
        response = _to_response(result)
        for item in response.messages:
            yield _sse("message", item.model_dump(mode="json"))
        if response.vehicle:
            yield _sse("vehicle", response.vehicle.model_dump(mode="json"))
        yield _sse("done", {"runId": str(result.run_id)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _reserve_quota(request: Request, subject: UsageSubject, quota: UsageQuotaService) -> None:
    settings = request.app.state.settings
    limit = (
        settings.registered_text_daily_limit
        if subject.kind == "registered"
        else settings.guest_text_daily_limit
    )
    try:
        await quota.reserve_text(subject, limit)
    except UsageQuotaExceededError as exc:
        raise AppError(
            "TEXT_DAILY_QUOTA_EXCEEDED",
            "今日文本请求次数已用完，请明日再试。",
            status_code=429,
        ) from exc


async def _run(
    service: CockpitAgentService,
    request: Request,
    message: str,
    session_id: str | None,
    vehicle_id: UUID,
) -> AgentResult:
    try:
        return await service.run(
            request_id=request.state.request_id,
            conversation_id=_optional_uuid(session_id),
            vehicle_id=vehicle_id,
            text=message,
        )
    except Exception as exc:
        raise AppError(
            "AGENT_EXECUTION_FAILED",
            "智能座舱请求暂时无法完成",
            status_code=503,
        ) from exc


async def _resolve_vehicle(request: Request, subject: UsageSubject, garage: GarageService) -> UUID:
    try:
        return await garage.resolve_vehicle_id(
            user_id=subject.user_id,
            requested_vehicle_id=None,
            demo_vehicle_id=request.app.state.settings.default_vehicle_id,
        )
    except ProductNotFoundError as exc:
        raise AppError("VEHICLE_NOT_FOUND", "Vehicle was not found", status_code=404) from exc


def _to_response(result: AgentResult) -> SendChatResponse:
    safety_reason = next(
        (item.get("safetyReason") for item in result.outcomes if item["status"] == "BLOCKED"),
        None,
    )
    message = ChatMessage(
        id=str(uuid4()),
        role="assistant",
        kind="safety_warning" if result.blocked else "assistant",
        content=result.response_text,
        at=datetime.now(UTC),
        tools=[
            ToolCallView(
                name=item["name"],
                params=item["params"],
                status=item["status"],
                durationMs=item["durationMs"],
            )
            for item in result.outcomes
        ]
        or None,
        meta=ChatMessageMeta(
            model=result.model,
            latencyMs=result.latency_ms,
            blocked=result.blocked,
            safetyReason=safety_reason,
            runId=str(result.run_id),
            llmCalls=result.llm_calls,
        ),
    )
    state = result.vehicle_state
    vehicle = CockpitVehicleState(
        speed=state.speed_kph,
        gear=state.gear,
        batterySoc=state.battery_soc,
        rangeKm=state.range_km,
        driverTemperature=state.climate["driver"],
        passengerTemperature=state.climate["passenger"],
        driverSeatHeat=state.seat_heat["driver"],
        passengerSeatHeat=state.seat_heat["passenger"],
        acStatus=(
            "ON"
            if state.climate["driver"] != 22
            or state.climate["passenger"] != 22
            or any(state.seat_heat.values())
            else "OFF"
        ),
        windowFL=state.window_position["driver"],
        windowFR=state.window_position["passenger"],
        headlight="OFF" if state.light_state == "OFF" else "ON",
        chargeStatus=state.charge_status,
    )
    return SendChatResponse(messages=[message], vehicle=vehicle)


def _optional_uuid(value: str | None) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(value)
    except ValueError:
        return uuid5(NAMESPACE_URL, f"automind-session:{value}")


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
