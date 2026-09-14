from html import escape
from time import perf_counter

from apps.api.aigc.providers.base import ImageGenerationResult


class MockImageGenerationProvider:
    name = "mock"
    model = "automind-svg-v1"
    is_external = False

    async def generate(self, prompt: str) -> ImageGenerationResult:
        started = perf_counter()
        safe_prompt = escape(prompt[:160])
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" '
            'viewBox="0 0 1600 900">'
            '<defs><linearGradient id="sky" x1="0" y1="0" x2="1" y2="1">'
            '<stop stop-color="#06152f"/><stop offset="0.55" stop-color="#12375a"/>'
            '<stop offset="1" stop-color="#087f8c"/></linearGradient>'
            '<radialGradient id="glow"><stop stop-color="#59dbe8" stop-opacity=".35"/>'
            '<stop offset="1" stop-color="#06152f" stop-opacity="0"/></radialGradient></defs>'
            '<rect width="1600" height="900" fill="url(#sky)"/>'
            '<circle cx="1250" cy="170" r="250" fill="url(#glow)"/>'
            '<path d="M0 610 Q250 530 500 630 T1000 620 T1600 560 V900 H0Z" '
            'fill="#071322" opacity=".9"/>'
            '<path d="M0 690 Q360 600 720 700 T1450 650 T1600 640" fill="none" '
            'stroke="#50c9d7" stroke-opacity=".28" stroke-width="7"/>'
            f"<metadata>{safe_prompt}</metadata></svg>"
        )
        return ImageGenerationResult(
            content=svg.encode(),
            content_type="image/svg+xml",
            provider=self.name,
            model=self.model,
            latency_ms=round((perf_counter() - started) * 1000),
            cost_est_cny=0,
        )
