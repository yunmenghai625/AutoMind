import hashlib
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.agents.service import CockpitAgentService
from apps.api.agents.trace import AgentTraceStore
from apps.api.aigc.providers.image_provider import OpenAICompatibleImageProvider
from apps.api.aigc.providers.mock_provider import MockImageGenerationProvider
from apps.api.aigc.repository import AigcRepository, UsageSubject
from apps.api.aigc.service import ThemeApplyService, ThemeGenerationService
from apps.api.aigc.storage import LocalThemeAssetStore, S3ThemeAssetStore
from apps.api.aigc.theme_generator import LocalThemeGenerator, OpenAICompatibleThemeGenerator
from apps.api.auth.service import AuthenticationError, AuthIdentity, JwtAuthenticator
from apps.api.core.errors import AppError
from apps.api.diagnosis.image_guard import ImageGuard
from apps.api.diagnosis.providers.local_provider import LocalHeuristicVlmProvider
from apps.api.diagnosis.providers.openai_compatible import OpenAICompatibleVlmProvider
from apps.api.diagnosis.repository import DiagnosisRepository
from apps.api.diagnosis.service import DiagnosisService
from apps.api.domain.vehicle.service import VehicleService
from apps.api.infrastructure.agent_trace import PostgresAgentTraceStore
from apps.api.infrastructure.database import get_session_factory
from apps.api.infrastructure.knowledge_repository import PostgresKnowledgeRepository
from apps.api.infrastructure.storage import (
    LocalStorageProvider,
    S3CompatibleStorageProvider,
)
from apps.api.infrastructure.vehicle_hal import PostgresVehicleHAL
from apps.api.models.gateway import ModelGateway
from apps.api.operations.repository import OperationalRepository
from apps.api.operations.service import AdminMetricsService, BudgetGuard
from apps.api.product.repository import (
    ExternalDataRepository,
    FeedbackRepository,
    GarageRepository,
    PreferenceRepository,
    UsageQuotaRepository,
    UserRepository,
)
from apps.api.product.service import (
    ExternalVehicleDataService,
    FeedbackService,
    GarageService,
    PreferenceService,
    UsageQuotaService,
)
from apps.api.product.vehicle_data import (
    DisabledVehicleDataProvider,
    NhtsaVehicleDataProvider,
)
from apps.api.rag.embeddings import build_embedding_provider
from apps.api.rag.ingestion import DocumentIngestionService
from apps.api.rag.reranker import LocalOverlapReranker
from apps.api.rag.rewrite import RuleBasedQueryRewriter
from apps.api.rag.service import KnowledgeService


async def get_database_session(request: Request) -> AsyncIterator[AsyncSession]:
    session_factory = get_session_factory(request.app.state.settings)
    async with session_factory() as session:
        yield session


def get_vehicle_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> VehicleService:
    return VehicleService(PostgresVehicleHAL(session))


def get_agent_trace_store(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> PostgresAgentTraceStore:
    return PostgresAgentTraceStore(session)


def get_operational_repository(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> OperationalRepository:
    return OperationalRepository(session)


def get_admin_metrics_service(
    repository: Annotated[OperationalRepository, Depends(get_operational_repository)],
) -> AdminMetricsService:
    return AdminMetricsService(repository)


def get_budget_guard(
    request: Request,
    repository: Annotated[OperationalRepository, Depends(get_operational_repository)],
) -> BudgetGuard:
    settings = request.app.state.settings
    return BudgetGuard(
        repository,
        daily_limit=settings.daily_ai_budget_cny,
        economy_ratio=settings.budget_economy_threshold_ratio,
    )


async def get_cockpit_agent_service(
    request: Request,
    vehicle_service: Annotated[VehicleService, Depends(get_vehicle_service)],
    trace_store: Annotated[AgentTraceStore, Depends(get_agent_trace_store)],
    budget: Annotated[BudgetGuard, Depends(get_budget_guard)],
) -> CockpitAgentService:
    budget_state = await budget.current()
    return CockpitAgentService(
        vehicle_service=vehicle_service,
        trace_store=trace_store,
        model_gateway=ModelGateway(
            request.app.state.settings,
            economy_mode=budget_state.state != "normal",
        ),
    )


def get_knowledge_repository(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> PostgresKnowledgeRepository:
    return PostgresKnowledgeRepository(session)


def get_document_ingestion_service(
    request: Request,
    repository: Annotated[PostgresKnowledgeRepository, Depends(get_knowledge_repository)],
) -> DocumentIngestionService:
    settings = request.app.state.settings
    return DocumentIngestionService(
        repository=repository,
        embedding_provider=build_embedding_provider(settings),
        batch_size=settings.embedding_batch_size,
    )


def get_knowledge_service(
    request: Request,
    repository: Annotated[PostgresKnowledgeRepository, Depends(get_knowledge_repository)],
) -> KnowledgeService:
    settings = request.app.state.settings
    return KnowledgeService(
        repository=repository,
        embedding_provider=build_embedding_provider(settings),
        reranker=LocalOverlapReranker(),
        rewriter=RuleBasedQueryRewriter(),
        top_k=settings.rag_top_k,
        confidence_threshold=settings.rag_confidence_threshold,
        max_retries=settings.rag_max_retries,
    )


def get_aigc_repository(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> AigcRepository:
    return AigcRepository(session)


def get_auth_identity(request: Request) -> AuthIdentity:
    settings = request.app.state.settings
    authenticator = JwtAuthenticator(
        secret=settings.jwt_secret.get_secret_value() if settings.jwt_secret else "",
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    )
    try:
        identity = authenticator.authenticate(request.headers.get("Authorization"))
    except AuthenticationError as exc:
        raise AppError("AUTH_INVALID_TOKEN", str(exc), status_code=401) from exc
    request.state.user_id = identity.user_id
    return identity


def get_user_repository(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> UserRepository:
    return UserRepository(session)


async def get_registered_identity(
    identity: Annotated[AuthIdentity, Depends(get_auth_identity)],
    users: Annotated[UserRepository, Depends(get_user_repository)],
) -> AuthIdentity:
    if identity.user_id is None:
        raise AppError("AUTH_REQUIRED", "Registered account is required", status_code=401)
    user = await users.ensure(
        user_id=identity.user_id,
        email=identity.email,
        role=identity.role,
    )
    if user.status != "active":
        raise AppError("AUTH_ACCOUNT_DISABLED", "Account is disabled", status_code=403)
    return identity


async def get_admin_identity(
    identity: Annotated[AuthIdentity, Depends(get_registered_identity)],
) -> AuthIdentity:
    if identity.role != "admin":
        raise AppError("ADMIN_FORBIDDEN", "Administrator role is required", status_code=403)
    return identity


async def get_usage_subject(
    request: Request,
    identity: Annotated[AuthIdentity, Depends(get_auth_identity)],
    users: Annotated[UserRepository, Depends(get_user_repository)],
) -> UsageSubject:
    if identity.user_id is not None:
        user = await users.ensure(
            user_id=identity.user_id,
            email=identity.email,
            role=identity.role,
        )
        if user.status != "active":
            raise AppError("AUTH_ACCOUNT_DISABLED", "Account is disabled", status_code=403)
        return UsageSubject(
            kind="registered",
            key=f"user:{identity.user_id}",
            user_id=identity.user_id,
        )
    guest_hint = request.headers.get("X-Guest-ID")
    if not guest_hint:
        client_host = request.client.host if request.client else "unknown"
        guest_hint = f"{client_host}|{request.headers.get('User-Agent', '')}"
    digest = hashlib.sha256(guest_hint.encode()).hexdigest()
    return UsageSubject(kind="guest", key=f"guest:{digest}")


def get_theme_generation_service(
    request: Request,
    repository: Annotated[AigcRepository, Depends(get_aigc_repository)],
    knowledge_service: Annotated[KnowledgeService, Depends(get_knowledge_service)],
) -> ThemeGenerationService:
    settings = request.app.state.settings
    fallback = MockImageGenerationProvider()
    if settings.theme_provider == "openai_compatible":
        generator = OpenAICompatibleThemeGenerator(
            api_key=settings.llm_api_key.get_secret_value() if settings.llm_api_key else "",
            base_url=settings.llm_base_url,
            model=settings.theme_model or settings.llm_model,
            timeout_seconds=settings.llm_timeout_seconds,
            input_price_cny_per_million=settings.llm_input_price_cny_per_million,
            output_price_cny_per_million=settings.llm_output_price_cny_per_million,
        )
    else:
        generator = LocalThemeGenerator()
    if settings.image_provider == "openai_compatible":
        images = OpenAICompatibleImageProvider(
            api_key=settings.image_api_key.get_secret_value() if settings.image_api_key else "",
            base_url=settings.image_base_url,
            model=settings.image_model,
            timeout_seconds=settings.image_timeout_seconds,
            cost_est_cny=settings.image_cost_est_cny,
        )
    else:
        images = fallback
    if settings.aigc_asset_storage == "s3":
        store = S3ThemeAssetStore(
            endpoint=settings.r2_endpoint,
            bucket=settings.aigc_r2_bucket or settings.r2_bucket,
            access_key=settings.r2_access_key.get_secret_value() if settings.r2_access_key else "",
            secret_key=settings.r2_secret_key.get_secret_value() if settings.r2_secret_key else "",
            public_base_url=settings.r2_public_base_url,
            prefix=settings.aigc_storage_prefix,
            proxy_base_url=f"{settings.api_v1_prefix}/aigc/assets",
        )
    else:
        store = LocalThemeAssetStore(settings.aigc_local_asset_dir)
    return ThemeGenerationService(
        repository=repository,
        generator=generator,
        image_provider=images,
        fallback_provider=fallback,
        asset_store=store,
        guest_daily_limit=settings.aigc_guest_daily_limit,
        user_daily_limit=settings.aigc_user_daily_limit,
        monthly_image_budget_cny=settings.monthly_image_budget_cny,
        knowledge_service=knowledge_service,
    )


def get_theme_apply_service(
    repository: Annotated[AigcRepository, Depends(get_aigc_repository)],
    vehicle_service: Annotated[VehicleService, Depends(get_vehicle_service)],
    trace_store: Annotated[AgentTraceStore, Depends(get_agent_trace_store)],
) -> ThemeApplyService:
    return ThemeApplyService(
        repository=repository,
        vehicle_service=vehicle_service,
        trace_store=trace_store,
    )


def get_diagnosis_repository(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> DiagnosisRepository:
    return DiagnosisRepository(session)


def get_diagnosis_service(
    request: Request,
    repository: Annotated[DiagnosisRepository, Depends(get_diagnosis_repository)],
    trace_store: Annotated[AgentTraceStore, Depends(get_agent_trace_store)],
    knowledge_service: Annotated[KnowledgeService, Depends(get_knowledge_service)],
) -> DiagnosisService:
    settings = request.app.state.settings
    fallback = LocalHeuristicVlmProvider()
    if settings.vlm_provider == "openai_compatible":
        provider = OpenAICompatibleVlmProvider(
            api_key=settings.vlm_api_key.get_secret_value() if settings.vlm_api_key else "",
            base_url=settings.vlm_base_url,
            model=settings.vlm_model,
            timeout_seconds=settings.vlm_timeout_seconds,
            input_price_cny_per_million=settings.vlm_input_price_cny_per_million,
            output_price_cny_per_million=settings.vlm_output_price_cny_per_million,
        )
    else:
        provider = fallback
    if settings.diagnosis_asset_storage == "s3":
        storage = S3CompatibleStorageProvider(
            endpoint=settings.r2_endpoint,
            bucket=settings.diagnosis_r2_bucket or settings.r2_bucket,
            access_key=settings.r2_access_key.get_secret_value() if settings.r2_access_key else "",
            secret_key=(
                settings.r2_secret_key.get_secret_value() if settings.r2_secret_key else ""
            ),
            public_base_url=None,
            prefix=settings.diagnosis_storage_prefix,
        )
    else:
        storage = LocalStorageProvider(
            root=settings.diagnosis_local_asset_dir,
            public_prefix=f"{settings.api_v1_prefix}/diagnosis/assets",
        )
    return DiagnosisService(
        repository=repository,
        trace_store=trace_store,
        image_guard=ImageGuard(
            max_bytes=settings.image_upload_max_bytes,
            max_dimension=settings.image_max_dimension,
            max_pixels=settings.image_max_pixels,
            jpeg_quality=settings.image_jpeg_quality,
        ),
        storage=storage,
        vlm_provider=provider,
        fallback_provider=fallback,
        knowledge_service=knowledge_service,
        guest_daily_limit=settings.guest_image_daily_limit,
        user_daily_limit=settings.registered_image_daily_limit,
        confidence_threshold=settings.diagnosis_confidence_threshold,
        monthly_budget_cny=settings.monthly_ai_budget_cny,
        retention_days=settings.diagnosis_retention_days,
    )


def get_preference_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> PreferenceService:
    return PreferenceService(PreferenceRepository(session))


def get_garage_repository(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> GarageRepository:
    return GarageRepository(session)


def _vin_secret(request: Request) -> str:
    settings = request.app.state.settings
    if settings.vin_hash_secret and settings.vin_hash_secret.get_secret_value():
        return settings.vin_hash_secret.get_secret_value()
    if settings.jwt_secret and settings.jwt_secret.get_secret_value():
        return settings.jwt_secret.get_secret_value()
    return "automind-development-vin-hash"


def get_garage_service(
    request: Request,
    repository: Annotated[GarageRepository, Depends(get_garage_repository)],
) -> GarageService:
    return GarageService(repository, vin_secret=_vin_secret(request))


def get_external_data_repository(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> ExternalDataRepository:
    return ExternalDataRepository(session)


def get_external_vehicle_data_service(
    request: Request,
    repository: Annotated[ExternalDataRepository, Depends(get_external_data_repository)],
    garage: Annotated[GarageRepository, Depends(get_garage_repository)],
) -> ExternalVehicleDataService:
    settings = request.app.state.settings
    provider = getattr(request.app.state, "vehicle_data_provider", None)
    if provider is None:
        if settings.vehicle_data_provider == "nhtsa":
            provider = NhtsaVehicleDataProvider(
                vehicle_base_url=settings.vehicle_data_base_url,
                recall_base_url=settings.recall_data_base_url,
                timeout_seconds=settings.vehicle_data_timeout_seconds,
            )
        else:
            provider = DisabledVehicleDataProvider()
        request.app.state.vehicle_data_provider = provider
    return ExternalVehicleDataService(
        repository=repository,
        garage=garage,
        provider=provider,
        cache_ttl_hours=settings.vehicle_data_cache_ttl_hours,
        vin_secret=_vin_secret(request),
    )


def get_feedback_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> FeedbackService:
    return FeedbackService(FeedbackRepository(session))


def get_usage_quota_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> UsageQuotaService:
    return UsageQuotaService(
        UsageQuotaRepository(session),
        enabled=request.app.state.settings.usage_quota_enabled,
    )
