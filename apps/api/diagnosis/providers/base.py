from dataclasses import dataclass
from typing import Protocol

from apps.api.diagnosis.schemas import VlmStructuredOutput


@dataclass(frozen=True, slots=True)
class VlmAnalysisResult:
    output: VlmStructuredOutput
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    cost_est_cny: float


class VlmProvider(Protocol):
    name: str
    model: str
    is_external: bool

    async def analyze(
        self, *, image: bytes, mime_type: str, filename: str, context: str | None
    ) -> VlmAnalysisResult: ...
