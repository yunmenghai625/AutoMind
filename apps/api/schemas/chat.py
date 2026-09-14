from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class SendChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    sessionId: str | None = None
    history: list[ChatHistoryMessage] = Field(default_factory=list, max_length=20)


class ToolCallView(BaseModel):
    name: str
    params: dict[str, str | int | float | bool]
    status: Literal["SUCCESS", "RUNNING", "FAILED", "BLOCKED"]
    durationMs: int | None = None


class ChatMessageMeta(BaseModel):
    model: str | None = None
    latencyMs: int
    blocked: bool
    safetyReason: str | None = None
    runId: str
    llmCalls: int


class ChatMessage(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    kind: Literal["user", "assistant", "tool_call", "tool_result", "safety_warning", "system_event"]
    content: str
    at: datetime
    tools: list[ToolCallView] | None = None
    meta: ChatMessageMeta | None = None


class CockpitVehicleState(BaseModel):
    speed: float
    gear: str
    batterySoc: float
    rangeKm: float
    driverTemperature: float
    passengerTemperature: float
    driverSeatHeat: int
    passengerSeatHeat: int
    acStatus: Literal["ON", "OFF"]
    windowFL: float
    windowFR: float
    headlight: str
    chargeStatus: str


class SendChatResponse(BaseModel):
    messages: list[ChatMessage]
    vehicle: CockpitVehicleState | None = None


class StreamEvent(BaseModel):
    event: str
    data: dict[str, Any]
