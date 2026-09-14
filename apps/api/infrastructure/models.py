from datetime import date as date_type
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Computed,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ServiceMetadata(Base):
    __tablename__ = "service_metadata"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class UserRecord(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    role: Mapped[str] = mapped_column(String(40), nullable=False, default="authenticated")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint("status IN ('active', 'disabled')", name="ck_users_status"),
        Index("ix_users_email", "email"),
    )


class UserPreferenceRecord(Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    preferred_temp_c: Mapped[float] = mapped_column(Float, nullable=False, default=23)
    seat_heat_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    charge_limit_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=80)
    driving_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="Comfort")
    preferences_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint("preferred_temp_c BETWEEN 16 AND 30", name="ck_preferences_temperature"),
        CheckConstraint("seat_heat_level BETWEEN 0 AND 3", name="ck_preferences_seat_heat"),
        CheckConstraint(
            "charge_limit_percent BETWEEN 50 AND 100", name="ck_preferences_charge_limit"
        ),
        CheckConstraint(
            "driving_mode IN ('Comfort', 'Sport', 'Eco')", name="ck_preferences_driving_mode"
        ),
    )


class VehicleRecord(Base):
    __tablename__ = "vehicles"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    make: Mapped[str] = mapped_column(String(80), nullable=False)
    model: Mapped[str] = mapped_column(String(80), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    powertrain: Mapped[str] = mapped_column(String(30), nullable=False)
    vin_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    vin_last4: Mapped[str | None] = mapped_column(String(4), nullable=True)
    mileage_km: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint("year BETWEEN 1886 AND 2100", name="ck_vehicles_year"),
        CheckConstraint("mileage_km >= 0", name="ck_vehicles_mileage_nonnegative"),
    )


class VehicleStateRecord(Base):
    __tablename__ = "vehicle_states"

    vehicle_id: Mapped[UUID] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), primary_key=True
    )
    speed_kph: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    gear: Mapped[str] = mapped_column(String(1), nullable=False, default="P")
    battery_soc: Mapped[float] = mapped_column(Float, nullable=False, default=78)
    range_km: Mapped[float] = mapped_column(Float, nullable=False, default=421)
    climate_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    seat_heat_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    window_position_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    door_state_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    light_state: Mapped[str] = mapped_column(String(20), nullable=False, default="OFF")
    charge_status: Mapped[str] = mapped_column(String(20), nullable=False, default="IDLE")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint("speed_kph >= 0", name="ck_vehicle_states_speed_nonnegative"),
        CheckConstraint("gear IN ('P', 'R', 'N', 'D')", name="ck_vehicle_states_gear"),
        CheckConstraint("battery_soc BETWEEN 0 AND 100", name="ck_vehicle_states_battery_soc"),
        CheckConstraint("range_km >= 0", name="ck_vehicle_states_range_nonnegative"),
        CheckConstraint("version >= 0", name="ck_vehicle_states_version_nonnegative"),
    )


class VehicleStateAuditRecord(Base):
    __tablename__ = "vehicle_state_audits"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    vehicle_id: Mapped[UUID] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False
    )
    request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    property_name: Mapped[str] = mapped_column(String(40), nullable=False)
    zone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    old_value_json: Mapped[Any] = mapped_column(JSONB, nullable=False)
    new_value_json: Mapped[Any] = mapped_column(JSONB, nullable=False)
    state_version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_vehicle_state_audits_vehicle_created", "vehicle_id", "created_at"),
        Index("ix_vehicle_state_audits_request_id", "request_id"),
    )


class AgentRunRecord(Base):
    __tablename__ = "agent_runs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    request_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    trace_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    traffic_class: Mapped[str] = mapped_column(
        String(20), nullable=False, default="user", server_default="user"
    )
    conversation_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    agent_name: Mapped[str] = mapped_column(String(80), nullable=False)
    model: Mapped[str | None] = mapped_column(String(160), nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    token_in: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    token_out: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_est_cny: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False, default=0)
    llm_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    response_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("latency_ms >= 0", name="ck_agent_runs_latency_nonnegative"),
        CheckConstraint(
            "token_in >= 0 AND token_out >= 0", name="ck_agent_runs_tokens_nonnegative"
        ),
        CheckConstraint("llm_calls >= 0", name="ck_agent_runs_llm_calls_nonnegative"),
        CheckConstraint(
            "traffic_class IN ('user', 'load_test')", name="ck_agent_runs_traffic_class"
        ),
        Index("ix_agent_runs_created_at", "created_at"),
        Index("ix_agent_runs_traffic_created", "traffic_class", "created_at"),
    )


class AgentStepRecord(Base):
    __tablename__ = "agent_steps"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    node_name: Mapped[str] = mapped_column(String(80), nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    input_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("sequence > 0", name="ck_agent_steps_sequence_positive"),
        CheckConstraint("latency_ms >= 0", name="ck_agent_steps_latency_nonnegative"),
        Index("ux_agent_steps_run_sequence", "run_id", "sequence", unique=True),
    )


class ToolCallRecord(Base):
    __tablename__ = "tool_calls"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False
    )
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    arguments_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    result_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    safety_decision: Mapped[str] = mapped_column(String(20), nullable=False)
    safety_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("latency_ms >= 0", name="ck_tool_calls_latency_nonnegative"),
        Index("ix_tool_calls_run_created", "run_id", "created_at"),
    )


class KnowledgeDocumentRecord(Base):
    __tablename__ = "documents"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    source_key: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    source_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="indexing")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint("page_count >= 0 AND chunk_count >= 0", name="ck_documents_counts"),
        CheckConstraint("version > 0", name="ck_documents_version_positive"),
        Index("ix_documents_status_updated", "status", "updated_at"),
    )


class KnowledgeChunkRecord(Base):
    __tablename__ = "chunks"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    section: Mapped[str | None] = mapped_column(String(300), nullable=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    fts_text: Mapped[str] = mapped_column(Text, nullable=False)
    search_vector: Mapped[Any] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('simple', coalesce(fts_text, ''))", persisted=True),
        nullable=False,
    )
    embedding: Mapped[list[float]] = mapped_column(Vector(384), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(160), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("ordinal >= 0", name="ck_chunks_ordinal_nonnegative"),
        CheckConstraint("page_number IS NULL OR page_number > 0", name="ck_chunks_page_positive"),
        CheckConstraint("token_count > 0", name="ck_chunks_token_count_positive"),
        Index("ux_chunks_document_ordinal", "document_id", "ordinal", unique=True),
        Index("ix_chunks_search_vector", "search_vector", postgresql_using="gin"),
        Index(
            "ix_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


class RagQueryRecord(Base):
    __tablename__ = "rag_queries"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    request_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    trace_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    traffic_class: Mapped[str] = mapped_column(
        String(20), nullable=False, default="user", server_default="user"
    )
    original_query: Mapped[str] = mapped_column(Text, nullable=False)
    rewritten_query: Mapped[str] = mapped_column(Text, nullable=False)
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    retrieved_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    low_confidence: Mapped[bool] = mapped_column(nullable=False, default=False)
    top_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    vector_search_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rerank_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("retry_count BETWEEN 0 AND 2", name="ck_rag_queries_retry_count"),
        CheckConstraint("retrieved_count >= 0", name="ck_rag_queries_retrieved_count"),
        CheckConstraint("vector_search_ms >= 0 AND rerank_ms >= 0", name="ck_rag_queries_latency"),
        CheckConstraint(
            "traffic_class IN ('user', 'load_test')", name="ck_rag_queries_traffic_class"
        ),
        Index("ix_rag_queries_created_at", "created_at"),
        Index("ix_rag_queries_status_created", "status", "created_at"),
        Index("ix_rag_queries_traffic_created", "traffic_class", "created_at"),
    )


class RagHitRecord(Base):
    __tablename__ = "rag_hits"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    query_id: Mapped[UUID] = mapped_column(
        ForeignKey("rag_queries.id", ondelete="CASCADE"), nullable=False
    )
    chunk_id: Mapped[UUID] = mapped_column(
        ForeignKey("chunks.id", ondelete="CASCADE"), nullable=False
    )
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    vector_score: Mapped[float] = mapped_column(Float, nullable=False)
    text_score: Mapped[float] = mapped_column(Float, nullable=False)
    hybrid_score: Mapped[float] = mapped_column(Float, nullable=False)
    rerank_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    selected: Mapped[bool] = mapped_column(nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("attempt BETWEEN 0 AND 2", name="ck_rag_hits_attempt"),
        CheckConstraint("rank > 0", name="ck_rag_hits_rank_positive"),
        Index("ix_rag_hits_query_attempt_rank", "query_id", "attempt", "rank"),
    )


class AigcGenerationRecord(Base):
    __tablename__ = "aigc_generations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    subject_key: Mapped[str] = mapped_column(String(128), nullable=False)
    user_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    vehicle_id: Mapped[UUID] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(30), nullable=False, default="cockpit_theme")
    user_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    enhanced_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    model: Mapped[str] = mapped_column(String(160), nullable=False)
    image_provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    image_model: Mapped[str | None] = mapped_column(String(160), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_est_cny: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False, default=0)
    image_cost_est_cny: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False, default=0)
    output_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    cached: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    regenerated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    degraded_reason: Mapped[str | None] = mapped_column(String(80), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("latency_ms >= 0", name="ck_aigc_generations_latency"),
        CheckConstraint("cost_est_cny >= 0", name="ck_aigc_generations_cost"),
        CheckConstraint("image_cost_est_cny >= 0", name="ck_aigc_generations_image_cost"),
        Index("ix_aigc_generations_subject_created", "subject_key", "created_at"),
        Index("ix_aigc_generations_prompt_hash", "prompt_hash"),
        Index("ix_aigc_generations_status_created", "status", "created_at"),
    )


class CockpitThemeRecord(Base):
    __tablename__ = "cockpit_themes"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    generation_id: Mapped[UUID] = mapped_column(
        ForeignKey("aigc_generations.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    user_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    subject_key: Mapped[str] = mapped_column(String(128), nullable=False)
    vehicle_id: Mapped[UUID] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    theme_spec_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    wallpaper_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    is_favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    applied_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint("applied_count >= 0", name="ck_cockpit_themes_applied_count"),
        Index("ix_cockpit_themes_subject_created", "subject_key", "created_at"),
        Index("ix_cockpit_themes_prompt_hash", "prompt_hash"),
    )


class UsageDailyRecord(Base):
    __tablename__ = "usage_daily"

    date: Mapped[date_type] = mapped_column(primary_key=True)
    subject_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    user_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    requests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    text_requests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    aigc_requests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    image_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    diagnosis_requests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_est_cny: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "requests >= 0 AND text_requests >= 0 AND aigc_requests >= 0 "
            "AND tokens >= 0 AND image_calls >= 0",
            name="ck_usage_daily_counts",
        ),
        CheckConstraint("diagnosis_requests >= 0", name="ck_usage_daily_diagnosis_requests"),
        CheckConstraint("cost_est_cny >= 0", name="ck_usage_daily_cost"),
    )


class DiagnosisRecord(Base):
    __tablename__ = "diagnosis_records"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    subject_key: Mapped[str] = mapped_column(String(128), nullable=False)
    vehicle_id: Mapped[UUID] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False
    )
    agent_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    original_file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    image_url: Mapped[str] = mapped_column(Text, nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    image_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    image_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(40), nullable=False)
    warning_type: Mapped[str] = mapped_column(String(80), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    visible_evidence_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    uncertainty: Mapped[str] = mapped_column(Text, nullable=False)
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    citations_json: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    requested_provider: Mapped[str] = mapped_column(String(80), nullable=False)
    requested_model: Mapped[str] = mapped_column(String(160), nullable=False)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    model: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_est_cny: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False, default=0)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("confidence BETWEEN 0 AND 1", name="ck_diagnosis_confidence"),
        CheckConstraint("latency_ms >= 0", name="ck_diagnosis_latency"),
        CheckConstraint("cost_est_cny >= 0", name="ck_diagnosis_cost"),
        Index("ix_diagnosis_subject_created", "subject_key", "created_at"),
        Index("ix_diagnosis_status_created", "status", "created_at"),
        Index("ix_diagnosis_provider_model", "provider", "model"),
        Index("ix_diagnosis_image_expires", "image_expires_at"),
    )


class VehicleRecallRecord(Base):
    __tablename__ = "vehicle_recalls"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    vehicle_id: Mapped[UUID] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False
    )
    external_id: Mapped[str] = mapped_column(String(120), nullable=False)
    component: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    consequence: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_action: Mapped[str] = mapped_column(Text, nullable=False)
    risk: Mapped[str] = mapped_column(String(20), nullable=False)
    source: Mapped[str] = mapped_column(String(80), nullable=False)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint("risk IN ('Low', 'Medium', 'High')", name="ck_vehicle_recalls_risk"),
        UniqueConstraint("vehicle_id", "external_id", name="ux_vehicle_recalls_external"),
        Index("ix_vehicle_recalls_vehicle_expires", "vehicle_id", "expires_at"),
    )


class VehicleDataCacheRecord(Base):
    __tablename__ = "vehicle_data_cache"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    vehicle_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=True
    )
    cache_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    data_type: Mapped[str] = mapped_column(String(30), nullable=False)
    normalized_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    source: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "data_type IN ('vin_decode', 'recalls')", name="ck_vehicle_data_cache_type"
        ),
        Index("ix_vehicle_data_cache_vehicle_type", "vehicle_id", "data_type"),
        Index("ix_vehicle_data_cache_expires", "expires_at"),
    )


class FeedbackRecord(Base):
    __tablename__ = "feedback"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    subject_key: Mapped[str] = mapped_column(String(128), nullable=False)
    run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=True
    )
    message_id: Mapped[UUID | None] = mapped_column(nullable=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(80), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint("rating IN (-1, 1)", name="ck_feedback_rating"),
        CheckConstraint("run_id IS NOT NULL OR message_id IS NOT NULL", name="ck_feedback_target"),
        UniqueConstraint("subject_key", "run_id", name="ux_feedback_subject_run"),
        UniqueConstraint("subject_key", "message_id", name="ux_feedback_subject_message"),
        Index("ix_feedback_run_created", "run_id", "created_at"),
        Index("ix_feedback_subject_created", "subject_key", "created_at"),
    )


class HttpRequestMetricRecord(Base):
    __tablename__ = "http_request_metrics"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    request_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    trace_id: Mapped[str] = mapped_column(String(32), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    path: Mapped[str] = mapped_column(String(255), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    traffic_class: Mapped[str] = mapped_column(
        String(20), nullable=False, default="user", server_default="user"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("status_code BETWEEN 100 AND 599", name="ck_http_metrics_status"),
        CheckConstraint("duration_ms >= 0", name="ck_http_metrics_latency"),
        CheckConstraint(
            "traffic_class IN ('user', 'load_test')", name="ck_http_metrics_traffic_class"
        ),
        Index("ix_http_metrics_created", "created_at"),
        Index("ix_http_metrics_traffic_created", "traffic_class", "created_at"),
        Index("ix_http_metrics_status_created", "status_code", "created_at"),
        Index("ix_http_metrics_trace_id", "trace_id"),
    )
