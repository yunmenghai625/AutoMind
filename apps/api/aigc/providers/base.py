from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ImageGenerationResult:
    content: bytes
    content_type: str
    provider: str
    model: str
    latency_ms: int
    cost_est_cny: float


class ImageGenerationProvider(Protocol):
    name: str
    model: str
    is_external: bool

    async def generate(self, prompt: str) -> ImageGenerationResult: ...
