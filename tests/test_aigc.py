from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from apps.api.aigc.providers.base import ImageGenerationResult
from apps.api.aigc.providers.mock_provider import MockImageGenerationProvider
from apps.api.aigc.repository import StoredTheme, UsageSubject
from apps.api.aigc.schemas import ApplyThemeRequest, ThemeSpec
from apps.api.aigc.service import (
    AigcQuotaExceededError,
    ThemeApplyService,
    ThemeGenerationService,
)
from apps.api.aigc.theme_generator import LocalThemeGenerator
from apps.api.domain.vehicle.service import VehicleService
from tests.fakes import DEMO_VEHICLE_ID, InMemoryAgentTraceStore, InMemoryVehicleHAL


class MemoryAssetStore:
    def __init__(self) -> None:
        self.items: dict[str, bytes] = {}

    async def put(self, key: str, content: bytes, content_type: str) -> str:
        del content_type
        self.items[key] = content
        return f"/assets/{Path(key).name}"


class MemoryAigcRepository:
    def __init__(self, *, monthly_cost: float = 0) -> None:
        self.themes: dict[UUID, StoredTheme] = {}
        self.cache: dict[tuple[str, str], StoredTheme] = {}
        self.usage: dict[str, int] = {}
        self.monthly_cost = monthly_cost
        self.applied: list[UUID] = []
        self.generations: list[dict[str, Any]] = []

    async def reserve_daily_request(self, subject: UsageSubject, limit: int) -> int | None:
        used = self.usage.get(subject.key, 0)
        if used >= limit:
            return None
        self.usage[subject.key] = used + 1
        return used + 1

    async def add_usage(self, subject: UsageSubject, **values: Any) -> None:
        del subject, values

    async def monthly_external_image_cost(self) -> float:
        return self.monthly_cost

    async def find_cached(self, subject: UsageSubject, prompt_hash: str) -> StoredTheme | None:
        return self.cache.get((subject.key, prompt_hash))

    async def save_generation(self, **values: Any) -> StoredTheme:
        theme = StoredTheme(
            id=uuid4(),
            generation_id=uuid4(),
            spec=values["spec"],
            wallpaper_url=values["wallpaper_url"],
            subject_key=values["subject"].key,
            prompt_hash=values["prompt_hash"],
            vehicle_id=values["vehicle_id"],
        )
        self.themes[theme.id] = theme
        self.cache[(theme.subject_key, theme.prompt_hash)] = theme
        self.generations.append(values)
        return theme

    async def get_theme(self, theme_id: UUID, subject: UsageSubject) -> StoredTheme | None:
        theme = self.themes.get(theme_id)
        return theme if theme and theme.subject_key == subject.key else None

    async def mark_applied(self, theme_id: UUID) -> None:
        self.applied.append(theme_id)


class FailingExternalImageProvider:
    name = "external-test"
    model = "image-test-v1"
    is_external = True
    calls = 0

    async def generate(self, prompt: str) -> ImageGenerationResult:
        del prompt
        self.calls += 1
        raise TimeoutError


class CountingExternalImageProvider(FailingExternalImageProvider):
    async def generate(self, prompt: str) -> ImageGenerationResult:
        self.calls += 1
        return await MockImageGenerationProvider().generate(prompt)


def build_generation_service(
    repository: MemoryAigcRepository,
    image_provider: Any | None = None,
) -> ThemeGenerationService:
    fallback = MockImageGenerationProvider()
    return ThemeGenerationService(
        repository=repository,
        generator=LocalThemeGenerator(),
        image_provider=image_provider or fallback,
        fallback_provider=fallback,
        asset_store=MemoryAssetStore(),
        guest_daily_limit=2,
        user_daily_limit=3,
        monthly_image_budget_cny=5,
    )


@pytest.mark.asyncio
async def test_economy_mode_skips_external_image_provider() -> None:
    repository = MemoryAigcRepository()
    external = CountingExternalImageProvider()
    service = build_generation_service(repository, external)

    result = await service.generate(
        subject=UsageSubject("guest", "guest:economy"),
        vehicle_id=DEMO_VEHICLE_ID,
        prompt="生成节能模式下的夜间主题",
        regenerate=True,
        request_id="economy-theme",
        economy_mode=True,
    )

    assert external.calls == 0
    assert result.metadata.budget_state == "economy"
    assert result.metadata.degraded_reason == "IMAGE_BUDGET_ECONOMY"


def test_theme_spec_is_strict_and_confirmation_must_be_true() -> None:
    with pytest.raises(ValidationError):
        ThemeSpec(
            name="bad",
            ambient_color="blue",
            ambient_brightness=120,
            display_mode="cinema",
            music_style="quiet",
            temperature=40,
            wallpaper_prompt="short",
        )
    with pytest.raises(ValidationError):
        ApplyThemeRequest(confirmed=False, expected_version=0)


@pytest.mark.asyncio
async def test_generate_is_preview_only_and_second_request_uses_cache() -> None:
    repository = MemoryAigcRepository()
    service = build_generation_service(repository)
    hal = InMemoryVehicleHAL()
    initial = hal.state
    subject = UsageSubject("guest", "guest:test")

    first = await service.generate(
        subject=subject,
        vehicle_id=DEMO_VEHICLE_ID,
        prompt="给我一个适合海边夜间驾驶的安静主题",
        regenerate=False,
        request_id="preview-one",
    )
    second = await service.generate(
        subject=subject,
        vehicle_id=DEMO_VEHICLE_ID,
        prompt="给我一个适合海边夜间驾驶的安静主题",
        regenerate=False,
        request_id="preview-two",
    )

    assert first.theme.spec.name == "静谧海岸"
    assert second.metadata.cached is True
    assert hal.state == initial
    assert repository.generations[0]["status"] == "success"
    assert repository.generations[1]["status"] == "cached"


@pytest.mark.asyncio
async def test_guest_and_registered_quotas_are_independent() -> None:
    repository = MemoryAigcRepository()
    service = build_generation_service(repository)
    guest = UsageSubject("guest", "guest:quota")
    user = UsageSubject("registered", "user:quota", uuid4())

    for index in range(2):
        await service.generate(
            subject=guest,
            vehicle_id=DEMO_VEHICLE_ID,
            prompt=f"安静主题 {index}",
            regenerate=True,
            request_id=f"guest-{index}",
        )
    with pytest.raises(AigcQuotaExceededError):
        await service.generate(
            subject=guest,
            vehicle_id=DEMO_VEHICLE_ID,
            prompt="超额",
            regenerate=True,
            request_id="guest-over",
        )
    for index in range(3):
        await service.generate(
            subject=user,
            vehicle_id=DEMO_VEHICLE_ID,
            prompt=f"注册用户主题 {index}",
            regenerate=True,
            request_id=f"user-{index}",
        )


@pytest.mark.asyncio
async def test_budget_guard_degrades_without_calling_external_image_provider() -> None:
    repository = MemoryAigcRepository(monthly_cost=4.1)
    external = FailingExternalImageProvider()
    service = build_generation_service(repository, external)
    result = await service.generate(
        subject=UsageSubject("guest", "guest:budget"),
        vehicle_id=DEMO_VEHICLE_ID,
        prompt="夜间安静主题",
        regenerate=False,
        request_id="budget-test",
    )
    assert external.calls == 0
    assert result.metadata.status == "degraded"
    assert result.metadata.budget_state == "economy"
    assert result.metadata.image_provider == "mock"


@pytest.mark.asyncio
async def test_apply_uses_safety_gate_tools_and_changes_vehicle_only_after_confirmation() -> None:
    repository = MemoryAigcRepository()
    subject = UsageSubject("guest", "guest:apply")
    theme = await repository.save_generation(
        subject=subject,
        vehicle_id=DEMO_VEHICLE_ID,
        user_prompt="舒适",
        enhanced_prompt="舒适",
        prompt_hash="hash",
        provider="local",
        model="test",
        image_provider="mock",
        image_model="mock",
        status="success",
        latency_ms=1,
        cost_est_cny=0,
        image_cost_est_cny=0,
        wallpaper_url="/assets/theme.svg",
        cached=False,
        regenerated=False,
        degraded_reason=None,
        metadata={},
        spec=ThemeSpec(
            name="凉爽专注",
            ambient_color="#123B5D",
            ambient_brightness=20,
            display_mode="focus",
            music_style="ambient",
            temperature=21,
            wallpaper_prompt="minimal cool driving wallpaper",
        ),
    )
    hal = InMemoryVehicleHAL()
    trace = InMemoryAgentTraceStore()
    service = ThemeApplyService(
        repository=repository,
        vehicle_service=VehicleService(hal),
        trace_store=trace,
    )

    applied = await service.apply(
        theme_id=theme.id,
        subject=subject,
        vehicle_id=DEMO_VEHICLE_ID,
        expected_version=0,
        request_id="apply-confirmed",
    )

    assert hal.state.climate == {"driver": 21, "passenger": 21}
    assert applied.vehicle_state_version == 2
    assert [call["tool_name"] for call in trace.tool_calls] == [
        "set_temperature",
        "set_temperature",
    ]
    assert all(call["safety_decision"] == "approved" for call in trace.tool_calls)
    assert repository.applied == [theme.id]
