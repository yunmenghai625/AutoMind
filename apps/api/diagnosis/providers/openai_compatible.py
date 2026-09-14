import base64
import json
from time import perf_counter
from typing import Any

import httpx
from pydantic import ValidationError

from apps.api.diagnosis.providers.base import VlmAnalysisResult
from apps.api.diagnosis.schemas import VlmStructuredOutput


class VlmProviderError(RuntimeError):
    pass


class OpenAICompatibleVlmProvider:
    name = "openai_compatible"
    is_external = True

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: float,
        input_price_cny_per_million: float,
        output_price_cny_per_million: float,
    ) -> None:
        self.model = model
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._input_price = input_price_cny_per_million
        self._output_price = output_price_cny_per_million

    async def analyze(
        self, *, image: bytes, mime_type: str, filename: str, context: str | None
    ) -> VlmAnalysisResult:
        del filename
        started = perf_counter()
        encoded = base64.b64encode(image).decode()
        input_tokens = 0
        output_tokens = 0
        repair = ""
        for attempt in range(2):
            payload = {
                "model": self.model,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "你是汽车仪表盘视觉识别器。只描述图片中可见证据，不作确定维修诊断。"
                            "输出必须严格符合提供的 JSON Schema，不得添加字段。" + repair
                        ),
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    {
                                        "context": context or "",
                                        "schema": VlmStructuredOutput.model_json_schema(),
                                    },
                                    ensure_ascii=False,
                                ),
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{encoded}",
                                    "detail": "low",
                                },
                            },
                        ],
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
                output = VlmStructuredOutput.model_validate_json(
                    body["choices"][0]["message"]["content"]
                )
                usage = body.get("usage") or {}
                input_tokens += int(usage.get("prompt_tokens") or 0)
                output_tokens += int(usage.get("completion_tokens") or 0)
                break
            except (
                httpx.HTTPError,
                KeyError,
                IndexError,
                TypeError,
                ValueError,
                ValidationError,
            ) as exc:
                if attempt == 1:
                    raise VlmProviderError("VLM structured analysis failed") from exc
                repair = " 上一次输出无效；这是唯一一次修复机会，请返回完整有效 JSON。"
        latency = round((perf_counter() - started) * 1000)
        cost = (input_tokens * self._input_price + output_tokens * self._output_price) / 1_000_000
        return VlmAnalysisResult(
            output=output,
            provider=self.name,
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency,
            cost_est_cny=cost,
        )
