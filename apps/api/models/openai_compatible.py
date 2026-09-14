import json
from time import perf_counter
from typing import Any

import httpx

from apps.api.domain.vehicle.entities import VehicleStateData
from apps.api.models.base import ModelPlanResult
from apps.api.tools.schemas import ModelPlan


class OpenAICompatibleError(RuntimeError):
    pass


class OpenAICompatiblePlanner:
    def __init__(
        self,
        *,
        provider: str,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: float,
        input_price_cny_per_million: float,
        output_price_cny_per_million: float,
    ) -> None:
        self._provider = provider
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout_seconds
        self._input_price = input_price_cny_per_million
        self._output_price = output_price_cny_per_million

    async def plan(
        self,
        text: str,
        state: VehicleStateData,
        tool_catalog: list[dict[str, object]],
    ) -> ModelPlanResult:
        started = perf_counter()
        payload = {
            "model": self._model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是 AutoMind 座舱意图规划器。只输出 JSON，不解释推理过程。"
                        "你只能从给定工具目录生成参数；安全是否允许由独立策略引擎决定。"
                        "JSON 必须符合 intent/reply/tool_calls，其中 intent 为 cockpit_control、"
                        "vehicle_info 或 unsupported。无法确定时不要调用工具。"
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "request": text,
                            "vehicle_state": {
                                "speed_kph": state.speed_kph,
                                "gear": state.gear,
                                "battery_soc": state.battery_soc,
                                "range_km": state.range_km,
                            },
                            "tools": tool_catalog,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=payload,
                )
            response.raise_for_status()
            body: dict[str, Any] = response.json()
            content = body["choices"][0]["message"]["content"]
            plan = ModelPlan.model_validate_json(content)
            usage = body.get("usage") or {}
            input_tokens = int(usage.get("prompt_tokens") or 0)
            output_tokens = int(usage.get("completion_tokens") or 0)
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise OpenAICompatibleError("Model planning request failed") from exc

        latency_ms = round((perf_counter() - started) * 1000)
        cost = (input_tokens * self._input_price + output_tokens * self._output_price) / 1_000_000
        return ModelPlanResult(
            plan=plan,
            provider=self._provider,
            model=self._model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            cost_est_cny=cost,
        )
