import base64

import httpx
import pytest

from apps.api.aigc.providers.image_provider import (
    ImageProviderError,
    OpenAICompatibleImageProvider,
)


class FakeAsyncClient:
    responses: dict[str, httpx.Response] = {}

    def __init__(self, **kwargs: object) -> None:
        assert kwargs["follow_redirects"] is True

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def post(self, url: str, **kwargs: object) -> httpx.Response:
        del kwargs
        return self.responses[url]

    async def get(self, url: str) -> httpx.Response:
        return self.responses[url]


def provider() -> OpenAICompatibleImageProvider:
    return OpenAICompatibleImageProvider(
        api_key="test-key",
        base_url="https://model.example/v1",
        model="qwen-image-plus",
        timeout_seconds=30,
        cost_est_cny=0.1,
    )


@pytest.mark.asyncio
async def test_image_provider_accepts_base64(monkeypatch: pytest.MonkeyPatch) -> None:
    content = b"png-content"
    request = httpx.Request("POST", "https://model.example/v1/images/generations")
    FakeAsyncClient.responses = {
        str(request.url): httpx.Response(
            200,
            json={"data": [{"b64_json": base64.b64encode(content).decode()}]},
            request=request,
        )
    }
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    result = await provider().generate("cockpit")

    assert result.content == content
    assert result.content_type == "image/png"


@pytest.mark.asyncio
async def test_image_provider_downloads_https_url(monkeypatch: pytest.MonkeyPatch) -> None:
    generate_url = "https://model.example/v1/images/generations"
    image_url = "https://assets.example/generated.webp"
    FakeAsyncClient.responses = {
        generate_url: httpx.Response(
            200,
            json={"data": [{"url": image_url}]},
            request=httpx.Request("POST", generate_url),
        ),
        image_url: httpx.Response(
            200,
            content=b"webp-content",
            headers={"content-type": "image/webp; charset=binary"},
            request=httpx.Request("GET", image_url),
        ),
    }
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    result = await provider().generate("cockpit")

    assert result.content == b"webp-content"
    assert result.content_type == "image/webp"


@pytest.mark.asyncio
async def test_image_provider_rejects_non_https_url(monkeypatch: pytest.MonkeyPatch) -> None:
    generate_url = "https://model.example/v1/images/generations"
    FakeAsyncClient.responses = {
        generate_url: httpx.Response(
            200,
            json={"data": [{"url": "http://internal.example/image.png"}]},
            request=httpx.Request("POST", generate_url),
        )
    }
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    with pytest.raises(ImageProviderError):
        await provider().generate("cockpit")
