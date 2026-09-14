from apps.api.core.config import Settings
from apps.api.core.telemetry import record_operation, span
from apps.api.domain.vehicle.entities import VehicleStateData
from apps.api.models.base import ModelPlanResult, PlannerModel
from apps.api.models.openai_compatible import OpenAICompatibleError, OpenAICompatiblePlanner


class ModelGatewayDisabled(RuntimeError):
    pass


class ModelGatewayError(RuntimeError):
    pass


class ModelGateway:
    def __init__(
        self,
        settings: Settings,
        planner: PlannerModel | None = None,
        *,
        economy_mode: bool = False,
    ) -> None:
        self._settings = settings
        self._planner = None if economy_mode else (planner or self._build_planner(settings))

    @property
    def enabled(self) -> bool:
        return self._planner is not None

    async def plan(
        self,
        text: str,
        state: VehicleStateData,
        tool_catalog: list[dict[str, object]],
    ) -> ModelPlanResult:
        if self._planner is None:
            raise ModelGatewayDisabled("LLM gateway is not configured")
        try:
            with span("llm.plan", {"gen_ai.operation.name": "planning"}):
                result = await self._planner.plan(text, state, tool_catalog)
            record_operation(
                "llm",
                status="success",
                latency_ms=result.latency_ms,
                tokens_in=result.input_tokens,
                tokens_out=result.output_tokens,
                cost_cny=result.cost_est_cny,
                name=result.model,
            )
            return result
        except OpenAICompatibleError as exc:
            record_operation("llm", status="failed", latency_ms=0, name="planner")
            raise ModelGatewayError("LLM gateway is temporarily unavailable") from exc

    @staticmethod
    def _build_planner(settings: Settings) -> PlannerModel | None:
        api_key = settings.llm_api_key.get_secret_value() if settings.llm_api_key else ""
        if not (api_key and settings.llm_base_url and settings.llm_model):
            return None
        return OpenAICompatiblePlanner(
            provider=settings.llm_provider,
            api_key=api_key,
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            timeout_seconds=settings.llm_timeout_seconds,
            input_price_cny_per_million=settings.llm_input_price_cny_per_million,
            output_price_cny_per_million=settings.llm_output_price_cny_per_million,
        )
