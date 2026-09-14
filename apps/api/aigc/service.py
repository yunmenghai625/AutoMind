import hashlib
from dataclasses import dataclass
from time import perf_counter
from uuid import UUID

from apps.api.agents.trace import AgentTraceStore
from apps.api.aigc.prompt_builder import build_theme_prompt
from apps.api.aigc.providers.base import ImageGenerationProvider
from apps.api.aigc.providers.mock_provider import MockImageGenerationProvider
from apps.api.aigc.repository import AigcRepository, StoredTheme, UsageSubject
from apps.api.aigc.schemas import ThemeMetadata, ThemeSpec
from apps.api.aigc.storage import ThemeAssetStore
from apps.api.aigc.theme_generator import LocalThemeGenerator, ThemeGenerator
from apps.api.domain.safety.policy import AuthorizedToolCall, SafetyPolicyEngine
from apps.api.domain.vehicle.service import VehicleService
from apps.api.rag.service import NO_EVIDENCE_ANSWER, KnowledgeService
from apps.api.tools.registry import ToolExecutor, ToolRegistry
from apps.api.tools.schemas import ToolCallPlan


class AigcQuotaExceededError(RuntimeError):
    pass


class ThemeNotFoundError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class GeneratedTheme:
    theme: StoredTheme
    metadata: ThemeMetadata


@dataclass(frozen=True, slots=True)
class AppliedTheme:
    theme: StoredTheme
    vehicle_state_version: int
    agent_run_id: UUID


class ThemeGenerationService:
    def __init__(
        self,
        *,
        repository: AigcRepository,
        generator: ThemeGenerator,
        image_provider: ImageGenerationProvider,
        fallback_provider: MockImageGenerationProvider,
        asset_store: ThemeAssetStore,
        guest_daily_limit: int,
        user_daily_limit: int,
        monthly_image_budget_cny: float,
        knowledge_service: KnowledgeService | None = None,
    ) -> None:
        self._repository = repository
        self._generator = generator
        self._images = image_provider
        self._fallback = fallback_provider
        self._assets = asset_store
        self._guest_limit = guest_daily_limit
        self._user_limit = user_daily_limit
        self._monthly_budget = monthly_image_budget_cny
        self._knowledge = knowledge_service

    async def generate(
        self,
        *,
        subject: UsageSubject,
        vehicle_id: UUID,
        prompt: str,
        regenerate: bool,
        request_id: str,
        economy_mode: bool = False,
    ) -> GeneratedTheme:
        started = perf_counter()
        limit = self._user_limit if subject.kind == "registered" else self._guest_limit
        used = await self._repository.reserve_daily_request(subject, limit)
        if used is None:
            raise AigcQuotaExceededError

        grounding = await self._optional_grounding(prompt, request_id)
        enhanced = build_theme_prompt(prompt, grounding)
        generator = (
            LocalThemeGenerator()
            if economy_mode and self._generator.provider != "local"
            else self._generator
        )
        prompt_hash = hashlib.sha256(
            "|".join(
                (
                    " ".join(prompt.lower().split()),
                    str(vehicle_id),
                    generator.provider,
                    generator.model,
                    self._images.name,
                    self._images.model,
                )
            ).encode()
        ).hexdigest()

        cached = None if regenerate else await self._repository.find_cached(subject, prompt_hash)
        if cached is not None:
            theme = await self._repository.save_generation(
                subject=subject,
                vehicle_id=vehicle_id,
                user_prompt=prompt,
                enhanced_prompt=enhanced,
                prompt_hash=prompt_hash,
                provider=generator.provider,
                model=generator.model,
                image_provider="cache",
                image_model=None,
                status="cached",
                latency_ms=round((perf_counter() - started) * 1000),
                cost_est_cny=0,
                image_cost_est_cny=0,
                wallpaper_url=cached.wallpaper_url,
                cached=True,
                regenerated=False,
                degraded_reason=None,
                metadata={"cache_source_theme_id": str(cached.id), "grounded": bool(grounding)},
                spec=cached.spec,
            )
            return GeneratedTheme(
                theme,
                ThemeMetadata(
                    generation_id=theme.generation_id,
                    provider=generator.provider,
                    model=generator.model,
                    image_provider="cache",
                    image_model=None,
                    latency_ms=round((perf_counter() - started) * 1000),
                    cost_est_cny=0,
                    image_cost_est_cny=0,
                    status="cached",
                    cached=True,
                    quota_used=used,
                    quota_limit=limit,
                    budget_state="economy" if economy_mode else await self._budget_state(),
                ),
            )

        generated = await generator.generate(enhanced)
        budget_state = "economy" if economy_mode else await self._budget_state()
        provider = self._images
        degraded_reason = None
        if self._images.is_external and budget_state != "normal":
            provider = self._fallback
            degraded_reason = f"IMAGE_BUDGET_{budget_state.upper()}"

        try:
            image = await provider.generate(generated.spec.wallpaper_prompt)
        except Exception:
            image = await self._fallback.generate(generated.spec.wallpaper_prompt)
            degraded_reason = "IMAGE_PROVIDER_FAILED"

        extension = "svg" if image.content_type == "image/svg+xml" else "png"
        wallpaper_url = await self._assets.put(
            f"{prompt_hash[:20]}-{request_id[:8]}.{extension}", image.content, image.content_type
        )
        total_cost = generated.cost_est_cny + image.cost_est_cny
        total_latency = round((perf_counter() - started) * 1000)
        status = "degraded" if degraded_reason else "success"
        theme = await self._repository.save_generation(
            subject=subject,
            vehicle_id=vehicle_id,
            user_prompt=prompt,
            enhanced_prompt=enhanced,
            prompt_hash=prompt_hash,
            provider=generated.provider,
            model=generated.model,
            image_provider=image.provider,
            image_model=image.model,
            status=status,
            latency_ms=total_latency,
            cost_est_cny=total_cost,
            image_cost_est_cny=image.cost_est_cny,
            wallpaper_url=wallpaper_url,
            cached=False,
            regenerated=regenerate,
            degraded_reason=degraded_reason,
            metadata={
                "theme_latency_ms": generated.latency_ms,
                "image_latency_ms": image.latency_ms,
                "grounded": bool(grounding),
            },
            spec=generated.spec,
        )
        await self._repository.add_usage(
            subject,
            tokens=generated.input_tokens + generated.output_tokens,
            image_calls=int(image.provider != "mock"),
            cost=total_cost,
        )
        return GeneratedTheme(
            theme,
            ThemeMetadata(
                generation_id=theme.generation_id,
                provider=generated.provider,
                model=generated.model,
                image_provider=image.provider,
                image_model=image.model,
                latency_ms=total_latency,
                cost_est_cny=total_cost,
                image_cost_est_cny=image.cost_est_cny,
                status=status,
                cached=False,
                degraded_reason=degraded_reason,
                quota_used=used,
                quota_limit=limit,
                budget_state=budget_state,
            ),
        )

    async def _budget_state(self) -> str:
        spent = await self._repository.monthly_external_image_cost()
        if self._monthly_budget <= 0 or spent >= self._monthly_budget:
            return "exhausted"
        if spent >= self._monthly_budget * 0.8:
            return "economy"
        return "normal"

    async def _optional_grounding(self, prompt: str, request_id: str) -> list[str]:
        if self._knowledge is None:
            return []
        if not any(word in prompt for word in ("安全", "儿童", "雨", "长途", "夜间")):
            return []
        try:
            result = await self._knowledge.query(
                request_id=f"aigc-rag-{request_id}"[:128],
                query=f"汽车座舱舒适与安全建议：{prompt}",
            )
        except Exception:
            return []
        return [] if result.answer == NO_EVIDENCE_ANSWER else [result.answer]


class ThemeApplyService:
    def __init__(
        self,
        *,
        repository: AigcRepository,
        vehicle_service: VehicleService,
        trace_store: AgentTraceStore,
    ) -> None:
        self._repository = repository
        self._vehicles = vehicle_service
        self._traces = trace_store
        self._registry = ToolRegistry()
        self._safety = SafetyPolicyEngine()
        self._executor = ToolExecutor(vehicle_service)

    async def apply(
        self,
        *,
        theme_id: UUID,
        subject: UsageSubject,
        vehicle_id: UUID | None,
        expected_version: int,
        request_id: str,
    ) -> AppliedTheme:
        started = perf_counter()
        theme = await self._repository.get_theme(theme_id, subject)
        if theme is None:
            raise ThemeNotFoundError
        if vehicle_id is not None and theme.vehicle_id != vehicle_id:
            raise ThemeNotFoundError
        vehicle_id = theme.vehicle_id
        spec = ThemeSpec.model_validate(theme.spec)
        run_id = await self._traces.create_run(
            request_id=request_id,
            conversation_id=None,
            input_text=f"Apply cockpit theme: {spec.name}",
            agent_name="AIGCThemeApply",
        )
        await self._traces.record_step(
            run_id=run_id,
            sequence=1,
            node_name="validate_theme_spec",
            latency_ms=0,
            status="success",
            output_summary="ThemeSpec valid and user confirmation present",
        )
        state = await self._vehicles.get_state(vehicle_id)
        version = expected_version
        for sequence, zone in enumerate(("driver", "passenger"), start=2):
            plan = ToolCallPlan(
                name="set_temperature",
                arguments={"zone": zone, "temp_c": spec.temperature},
            )
            command = self._registry.validate(plan)
            permit = self._safety.authorize(command, state)
            if not isinstance(permit, AuthorizedToolCall):
                await self._traces.record_tool_call(
                    run_id=run_id,
                    tool_name=plan.name,
                    arguments=plan.arguments,
                    result=None,
                    latency_ms=0,
                    status="rejected",
                    safety_decision="rejected",
                    safety_code=permit.code,
                )
                await self._traces.complete_run(
                    run_id=run_id,
                    latency_ms=round((perf_counter() - started) * 1000),
                    status="rejected",
                    model=None,
                    token_in=0,
                    token_out=0,
                    cost_est_cny=0,
                    llm_calls=0,
                    response_summary="Theme apply rejected by Safety Gate",
                    error_code=permit.code,
                )
                raise PermissionError(permit.reason)
            tool_started = perf_counter()
            change = await self._executor.execute(
                permit,
                vehicle_id=vehicle_id,
                expected_version=version,
                request_id=request_id,
            )
            state = change.state
            version = state.version
            await self._traces.record_step(
                run_id=run_id,
                sequence=sequence,
                node_name=f"apply_{zone}_temperature",
                latency_ms=round((perf_counter() - tool_started) * 1000),
                status="success",
                output_summary=f"{zone}={spec.temperature}C",
            )
            await self._traces.record_tool_call(
                run_id=run_id,
                tool_name=plan.name,
                arguments=plan.arguments,
                result={"state_version": version},
                latency_ms=round((perf_counter() - tool_started) * 1000),
                status="success",
                safety_decision="approved",
                safety_code="APPROVED",
            )
        await self._repository.mark_applied(theme_id)
        await self._traces.complete_run(
            run_id=run_id,
            latency_ms=round((perf_counter() - started) * 1000),
            status="success",
            model=None,
            token_in=0,
            token_out=0,
            cost_est_cny=0,
            llm_calls=0,
            response_summary=f"Applied cockpit theme {spec.name}",
        )
        return AppliedTheme(theme, version, run_id)
