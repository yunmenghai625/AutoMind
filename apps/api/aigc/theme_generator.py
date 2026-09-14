import json
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Protocol

import httpx
from pydantic import ValidationError

from apps.api.aigc.schemas import ThemeSpec


class InvalidThemeSpecError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ThemeGenerationResult:
    spec: ThemeSpec
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    cost_est_cny: float


class ThemeGenerator(Protocol):
    provider: str
    model: str

    async def generate(self, enhanced_prompt: str) -> ThemeGenerationResult: ...


class LocalThemeGenerator:
    provider = "local"
    model = "automind-theme-local-v1"

    async def generate(self, enhanced_prompt: str) -> ThemeGenerationResult:
        started = perf_counter()
        lowered = enhanced_prompt.lower()
        seaside = any(word in enhanced_prompt for word in ("海边", "海岸", "海洋", "沙滩"))
        night = "夜" in enhanced_prompt or "night" in lowered
        quiet = any(word in enhanced_prompt for word in ("安静", "宁静", "放松"))
        if seaside and night:
            name = "静谧海岸"
            color = "#123B5D"
            wallpaper = (
                "宁静海岸公路的蓝调夜景，远处月光映照海面，低对比度，"
                "极简高级汽车座舱横屏壁纸，无文字无人物"
            )
        else:
            name = "智能舒适"
            color = "#2F6B78" if quiet else "#3B82A0"
            wallpaper = "抽象流线与柔和环境光构成的高级汽车座舱横屏壁纸，低干扰，无文字无人物"
        spec = ThemeSpec(
            name=name,
            ambient_color=color,
            ambient_brightness=22 if night else 45,
            display_mode="night" if night else "comfort",
            music_style="静谧氛围音乐" if quiet else "轻柔电子音乐",
            temperature=22,
            wallpaper_prompt=wallpaper,
        )
        latency = round((perf_counter() - started) * 1000)
        return ThemeGenerationResult(spec, self.provider, self.model, 0, 0, latency, 0)


class OpenAICompatibleThemeGenerator:
    provider = "openai_compatible"

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

    async def generate(self, enhanced_prompt: str) -> ThemeGenerationResult:
        started = perf_counter()
        input_tokens = 0
        output_tokens = 0
        repair = ""
        for attempt in range(2):
            payload = {
                "model": self.model,
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "你是汽车座舱主题设计器，只输出符合给定 ThemeSpec 的 JSON。"
                            "不得添加额外字段。" + repair
                        ),
                    },
                    {"role": "user", "content": enhanced_prompt},
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
                usage = body.get("usage") or {}
                input_tokens += int(usage.get("prompt_tokens") or 0)
                output_tokens += int(usage.get("completion_tokens") or 0)
                spec = ThemeSpec.model_validate(json.loads(content))
                break
            except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError, ValidationError):
                if attempt == 1:
                    raise InvalidThemeSpecError("Provider returned an invalid ThemeSpec") from None
                repair = " 上一次输出无效，这是唯一一次修复机会；请重新输出完整、有效的 JSON。"
        latency = round((perf_counter() - started) * 1000)
        cost = (input_tokens * self._input_price + output_tokens * self._output_price) / 1_000_000
        return ThemeGenerationResult(
            spec, self.provider, self.model, input_tokens, output_tokens, latency, cost
        )
