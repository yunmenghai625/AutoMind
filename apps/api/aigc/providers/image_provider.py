import base64
from time import perf_counter
from typing import Any

import httpx

from apps.api.aigc.providers.base import ImageGenerationResult


class ImageProviderError(RuntimeError):
    pass


class OpenAICompatibleImageProvider:
    is_external = True

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: float,
        cost_est_cny: float,
    ) -> None:
        self.name = "openai_compatible"
        self.model = model
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._cost = cost_est_cny

    async def generate(self, prompt: str) -> ImageGenerationResult:
        started = perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/images/generations",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "size": "1536x1024",
                        "response_format": "b64_json",
                    },
                )
            response.raise_for_status()
            body: dict[str, Any] = response.json()
            encoded = body["data"][0]["b64_json"]
            content = base64.b64decode(encoded, validate=True)
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise ImageProviderError("Image generation request failed") from exc
        return ImageGenerationResult(
            content=content,
            content_type="image/png",
            provider=self.name,
            model=self.model,
            latency_ms=round((perf_counter() - started) * 1000),
            cost_est_cny=self._cost,
        )
