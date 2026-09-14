from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from time import perf_counter
from uuid import UUID, uuid4

from apps.api.agents.trace import AgentTraceStore
from apps.api.aigc.repository import UsageSubject
from apps.api.diagnosis.image_guard import ImageGuard
from apps.api.diagnosis.providers.base import VlmProvider
from apps.api.diagnosis.repository import DiagnosisRepository
from apps.api.diagnosis.risk import classify_risk, recommended_action
from apps.api.diagnosis.schemas import (
    DetectedWarningResponse,
    DiagnosisCause,
    DiagnosisCitation,
    DiagnosisMetadata,
    DiagnosisRecommendation,
    DiagnosisResponse,
)
from apps.api.infrastructure.storage import StorageProvider
from apps.api.rag.service import NO_EVIDENCE_ANSWER, KnowledgeService


class DiagnosisQuotaExceededError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class DiagnosisInput:
    content: bytes
    declared_mime: str | None
    filename: str
    context: str | None


class DiagnosisService:
    def __init__(
        self,
        *,
        repository: DiagnosisRepository,
        trace_store: AgentTraceStore,
        image_guard: ImageGuard,
        storage: StorageProvider,
        vlm_provider: VlmProvider,
        fallback_provider: VlmProvider,
        knowledge_service: KnowledgeService,
        guest_daily_limit: int,
        user_daily_limit: int,
        confidence_threshold: float,
        monthly_budget_cny: float,
        retention_days: int,
    ) -> None:
        self._repository = repository
        self._traces = trace_store
        self._guard = image_guard
        self._storage = storage
        self._vlm = vlm_provider
        self._fallback = fallback_provider
        self._knowledge = knowledge_service
        self._guest_limit = guest_daily_limit
        self._user_limit = user_daily_limit
        self._confidence_threshold = confidence_threshold
        self._monthly_budget = monthly_budget_cny
        self._retention_days = retention_days

    async def diagnose(
        self,
        *,
        request_id: str,
        subject: UsageSubject,
        vehicle_id: UUID,
        payload: DiagnosisInput,
        economy_mode: bool = False,
    ) -> DiagnosisResponse:
        started = perf_counter()
        guarded = self._guard.process(payload.content, payload.declared_mime)
        quota_limit = self._user_limit if subject.kind == "registered" else self._guest_limit
        quota_used = await self._repository.reserve_request(subject, quota_limit)
        if quota_used is None:
            raise DiagnosisQuotaExceededError

        run_id = await self._traces.create_run(
            request_id=request_id,
            conversation_id=None,
            input_text=payload.context or f"Analyze dashboard image {payload.filename}",
            agent_name="DiagnosisAgent",
        )
        await self._traces.record_step(
            run_id=run_id,
            sequence=1,
            node_name="image_guard",
            latency_ms=0,
            status="success",
            output_summary=(
                f"{guarded.original_width}x{guarded.original_height} -> "
                f"{guarded.width}x{guarded.height} JPEG"
            ),
        )
        image_expires_at = datetime.now(UTC) + timedelta(days=self._retention_days)
        stored = await self._storage.put(
            key=f"{uuid4()}.jpg",
            content=guarded.content,
            content_type=guarded.content_type,
        )
        await self._traces.record_step(
            run_id=run_id,
            sequence=2,
            node_name="object_storage",
            latency_ms=0,
            status="success",
            output_summary=f"compressed image retained until {image_expires_at.date()}",
        )

        requested_provider = self._vlm.name
        requested_model = self._vlm.model
        provider = self._vlm
        status = "success"
        error_code = None
        if self._vlm.is_external and economy_mode:
            provider = self._fallback
            status = "degraded"
            error_code = "VLM_DAILY_BUDGET_ECONOMY"
        elif (
            self._vlm.is_external and await self._repository.monthly_cost() >= self._monthly_budget
        ):
            provider = self._fallback
            status = "degraded"
            error_code = "VLM_BUDGET_EXHAUSTED"
        external_call = provider.is_external
        try:
            analysis = await provider.analyze(
                image=guarded.content,
                mime_type=guarded.content_type,
                filename=payload.filename,
                context=payload.context,
            )
        except Exception:
            analysis = await self._fallback.analyze(
                image=guarded.content,
                mime_type=guarded.content_type,
                filename=payload.filename,
                context=payload.context,
            )
            status = "degraded"
            error_code = "VLM_PROVIDER_FAILED"

        await self._traces.record_step(
            run_id=run_id,
            sequence=3,
            node_name="vlm_structured_detection",
            latency_ms=analysis.latency_ms,
            status=status,
            output_summary=(
                f"provider={analysis.provider}, model={analysis.model}, "
                f"detections={len(analysis.output.detections)}"
            ),
            error_code=error_code,
        )

        detections = sorted(
            analysis.output.detections,
            key=lambda item: item.confidence,
            reverse=True,
        )
        primary = detections[0]
        low_confidence = primary.confidence < self._confidence_threshold
        await self._traces.record_step(
            run_id=run_id,
            sequence=4,
            node_name="confidence_gate",
            latency_ms=0,
            status="low_confidence" if low_confidence else "success",
            output_summary=f"top_confidence={primary.confidence:.2f}",
        )

        retrieved_result = None
        if not low_confidence and primary.warning_type != "unknown":
            try:
                knowledge_result = await self._knowledge.query(
                    request_id=f"diagnosis-rag-{request_id}"[:128],
                    query=f"{primary.label} {primary.warning_type} 应如何安全处理",
                )
                if knowledge_result.answer != NO_EVIDENCE_ANSWER:
                    retrieved_result = knowledge_result
            except Exception:
                status = "degraded"
                error_code = error_code or "RAG_UNAVAILABLE"

        citations = [
            DiagnosisCitation(
                source=item.source,
                chapter=item.chapter,
                page=item.page,
                snippet=item.snippet,
            )
            for item in (retrieved_result.citations if retrieved_result else [])
        ]
        await self._traces.record_step(
            run_id=run_id,
            sequence=5,
            node_name="knowledge_retrieval",
            latency_ms=(
                retrieved_result.retrieval.vector_search_ms + retrieved_result.retrieval.rerank_ms
                if retrieved_result
                else 0
            ),
            status="success" if citations else "no_evidence",
            output_summary=f"citations={len(citations)}",
        )

        risks = [classify_risk(item, low_confidence=low_confidence) for item in detections]
        main_risk = risks[0]
        action_title, action_detail = recommended_action(main_risk)
        frontend_risk = {"Information": "Low", "Warning": "Medium", "Critical": "High"}
        detected = [
            DetectedWarningResponse(
                code=item.warning_code or item.warning_type.upper(),
                label=item.label,
                confidence=round(item.confidence * 100),
                risk=frontend_risk[risk],
            )
            for item, risk in zip(detections, risks, strict=True)
        ]
        if low_confidence:
            message = "无法可靠识别该仪表指示。请重新拍摄清晰近照，或提供 OBD 故障码。"
        else:
            message = f"识别到可能的{primary.label}。该结果仅用于信息参考，不能替代专业维修检查。"
        evidence_text = "；".join(primary.visible_evidence)
        causes = [
            DiagnosisCause(
                title="可能的警告类型",
                detail=(
                    f"图片可见证据：{evidence_text}。具体故障原因仍需结合车辆状态、"
                    "OBD 故障码和专业检测确认。"
                ),
            )
        ]
        if retrieved_result:
            causes.append(DiagnosisCause(title="知识库说明", detail=retrieved_result.answer))
        recommendations = [
            DiagnosisRecommendation(title=action_title, detail=action_detail),
            DiagnosisRecommendation(
                title="保留不确定性",
                detail=primary.uncertainty,
            ),
        ]
        total_latency = round((perf_counter() - started) * 1000)
        final_status = "low_confidence" if low_confidence and status == "success" else status
        await self._traces.record_step(
            run_id=run_id,
            sequence=6,
            node_name="response_composer",
            latency_ms=0,
            status=final_status,
            output_summary=f"risk={main_risk}; low_confidence={low_confidence}",
        )
        await self._traces.complete_run(
            run_id=run_id,
            latency_ms=total_latency,
            status=final_status,
            model=analysis.model,
            token_in=analysis.input_tokens,
            token_out=analysis.output_tokens,
            cost_est_cny=analysis.cost_est_cny,
            llm_calls=int(analysis.provider != "local"),
            response_summary=message,
            error_code=error_code,
        )
        diagnosis_id = await self._repository.save(
            subject=subject,
            vehicle_id=vehicle_id,
            agent_run_id=run_id,
            original_file_name=payload.filename,
            image_url=stored.url,
            storage_key=stored.key,
            image_sha256=guarded.sha256,
            image_expires_at=image_expires_at,
            mime_type=guarded.content_type,
            warning_type=primary.warning_type,
            confidence=primary.confidence,
            risk_level=main_risk,
            visible_evidence=primary.visible_evidence,
            uncertainty=primary.uncertainty,
            response_text=message,
            citations=[item.model_dump(mode="json") for item in citations],
            requested_provider=requested_provider,
            requested_model=requested_model,
            provider=analysis.provider,
            model=analysis.model,
            status=final_status,
            latency_ms=total_latency,
            cost_est_cny=analysis.cost_est_cny,
            error_code=error_code,
            metadata={
                "original_dimensions": [
                    guarded.original_width,
                    guarded.original_height,
                ],
                "processed_dimensions": [guarded.width, guarded.height],
                "compressed_bytes": len(guarded.content),
                "context_supplied": bool(payload.context),
                "structured_output": analysis.output.model_dump(mode="json"),
            },
        )
        await self._repository.add_usage(
            subject,
            tokens=analysis.input_tokens + analysis.output_tokens,
            external_call=external_call,
            cost=analysis.cost_est_cny,
        )
        return DiagnosisResponse(
            request_id=request_id,
            detected=detected,
            causes=causes,
            recommendations=recommendations,
            references=citations,
            pipeline=[
                "Image Guard",
                "Object Storage",
                "Vision Model",
                "Confidence Gate",
                "Knowledge Retrieval",
                "Risk Classification",
            ],
            processedAt=datetime.now(UTC),
            message=message,
            metadata=DiagnosisMetadata(
                diagnosis_id=diagnosis_id,
                run_id=run_id,
                provider=analysis.provider,
                model=analysis.model,
                latency_ms=total_latency,
                cost_est_cny=analysis.cost_est_cny,
                status=final_status,
                low_confidence=low_confidence,
                quota_used=quota_used,
                quota_limit=quota_limit,
                image_expires_at=image_expires_at,
            ),
        )
