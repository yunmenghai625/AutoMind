from typing import Any, Literal, TypedDict
from uuid import UUID

from apps.api.domain.vehicle.entities import VehicleStateData
from apps.api.tools.schemas import ToolCommand

RouteName = Literal["rule", "vehicle_info", "model"]


class AgentState(TypedDict, total=False):
    request_id: str
    run_id: UUID
    vehicle_id: UUID
    input_text: str
    vehicle_state: VehicleStateData
    route: RouteName
    intent: str
    planned_calls: list[dict[str, Any]]
    commands: list[ToolCommand]
    safety_actions: list[Any]
    outcomes: list[dict[str, Any]]
    observed_speed_kph: float | None
    reply_hint: str
    response_text: str
    step_sequence: int
    model: str | None
    llm_calls: int
    token_in: int
    token_out: int
    cost_est_cny: float
