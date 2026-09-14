import hashlib
import math
from typing import Protocol

import httpx

from apps.api.core.config import Settings
from apps.api.rag.text import lexical_tokens


class EmbeddingError(RuntimeError):
    pass


class EmbeddingProvider(Protocol):
    model_name: str
    dimensions: int

    async def embed_batch(self, texts: list[str]) -> list[list[float]]: ...


class HashingEmbeddingProvider:
    def __init__(self, *, dimensions: int = 384, model_name: str = "hash-embedding-v2") -> None:
        self.dimensions = dimensions
        self.model_name = model_name

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in lexical_tokens(text):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
            index = int.from_bytes(digest[:8], "big") % self.dimensions
            sign = 1.0 if digest[8] & 1 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        return [value / norm for value in vector] if norm else vector


class OpenAICompatibleEmbeddingProvider:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model_name: str,
        dimensions: int,
        timeout_seconds: float,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.dimensions = dimensions
        self._timeout = timeout_seconds

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/embeddings",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json={
                        "model": self.model_name,
                        "input": texts,
                        "dimensions": self.dimensions,
                    },
                )
            response.raise_for_status()
            data = sorted(response.json()["data"], key=lambda item: item["index"])
            vectors = [list(map(float, item["embedding"])) for item in data]
            if len(vectors) != len(texts) or any(
                len(vector) != self.dimensions for vector in vectors
            ):
                raise ValueError("Embedding response has an unexpected shape")
            return vectors
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise EmbeddingError("Embedding provider request failed") from exc


def build_embedding_provider(settings: Settings) -> EmbeddingProvider:
    if settings.embedding_provider == "hash":
        return HashingEmbeddingProvider(
            dimensions=settings.embedding_dimensions,
            model_name=settings.embedding_model,
        )
    api_key = settings.embedding_api_key.get_secret_value() if settings.embedding_api_key else ""
    if not (api_key and settings.embedding_base_url and settings.embedding_model):
        raise EmbeddingError("OpenAI-compatible embedding provider is not fully configured")
    return OpenAICompatibleEmbeddingProvider(
        api_key=api_key,
        base_url=settings.embedding_base_url,
        model_name=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
        timeout_seconds=settings.llm_timeout_seconds,
    )
