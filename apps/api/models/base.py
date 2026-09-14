from dataclasses import dataclass
from typing import Protocol

from apps.api.domain.vehicle.entities import VehicleStateData
from apps.api.tools.schemas import ModelPlan


@dataclass(frozen=True, slots=True)
class ModelPlanResult:
    plan: ModelPlan
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    cost_est_cny: float


class PlannerModel(Protocol):
    async def plan(
        self,
        text: str,
        state: VehicleStateData,
        tool_catalog: list[dict[str, object]],
    ) -> ModelPlanResult: ...
