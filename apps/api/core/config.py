from functools import lru_cache
from typing import Literal
from uuid import UUID

from pydantic import AliasChoices, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "test", "staging", "production"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "AutoMind API"
    app_version: str = "1.0.2"
    app_env: Environment = "development"
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"
    database_url: SecretStr = SecretStr(
        "postgresql+asyncpg://automind:automind@localhost:5432/automind"
    )
    database_healthcheck_enabled: bool = True
    database_connect_timeout_seconds: float = Field(default=2.0, gt=0, le=30)
    cors_origins: str = "http://localhost:3000"
    docs_enabled: bool = True
    jwt_secret: SecretStr | None = None
    jwt_issuer: str = ""
    jwt_audience: str = "authenticated"
    admin_username: str = "yunmenghai625"
    admin_password_hash: SecretStr | None = None
    admin_session_hours: int = Field(default=8, ge=1, le=24)
    default_vehicle_id: UUID = UUID("00000000-0000-0000-0000-000000000001")
    llm_provider: str = "qwen"
    llm_api_key: SecretStr | None = None
    llm_base_url: str = ""
    llm_model: str = ""
    llm_timeout_seconds: float = Field(default=20.0, gt=0, le=120)
    llm_input_price_cny_per_million: float = Field(default=0, ge=0)
    llm_output_price_cny_per_million: float = Field(default=0, ge=0)
    embedding_provider: Literal["hash", "openai_compatible"] = "hash"
    embedding_api_key: SecretStr | None = None
    embedding_base_url: str = ""
    embedding_model: str = "hash-embedding-v2"
    # The migration uses vector(384); keeping this literal prevents a runtime
    # provider setting from drifting away from the persisted schema.
    embedding_dimensions: Literal[384] = 384
    embedding_batch_size: int = Field(default=32, ge=1, le=128)
    rerank_provider: Literal["local"] = "local"
    rerank_model: str = "local-overlap-v1"
    rag_top_k: int = Field(default=5, ge=1, le=20)
    rag_confidence_threshold: float = Field(default=0.24, ge=0, le=1)
    rag_max_retries: int = Field(default=2, ge=0, le=2)
    theme_provider: Literal["local", "openai_compatible"] = "local"
    theme_model: str = "automind-theme-local-v1"
    image_provider: Literal["mock", "openai_compatible"] = "mock"
    image_api_key: SecretStr | None = None
    image_base_url: str = "https://api.openai.com/v1"
    image_model: str = "gpt-image-1-mini"
    image_timeout_seconds: float = Field(default=30.0, gt=0, le=120)
    image_cost_est_cny: float = Field(default=0.08, ge=0)
    aigc_guest_daily_limit: int = Field(default=1, ge=1, le=100)
    aigc_user_daily_limit: int = Field(default=3, ge=1, le=1000)
    monthly_image_budget_cny: float = Field(default=5.0, ge=0)
    aigc_storage_prefix: str = "cockpit-themes/"
    aigc_asset_storage: Literal["local", "s3"] = "local"
    aigc_local_asset_dir: str = "data/generated/cockpit-themes"
    r2_endpoint: str = Field(
        default="", validation_alias=AliasChoices("R2_ENDPOINT", "AWS_ENDPOINT_URL")
    )
    r2_bucket: str = Field(
        default="", validation_alias=AliasChoices("R2_BUCKET", "AWS_S3_BUCKET_NAME")
    )
    aigc_r2_bucket: str = ""
    diagnosis_r2_bucket: str = ""
    r2_access_key: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("R2_ACCESS_KEY", "AWS_ACCESS_KEY_ID")
    )
    r2_secret_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("R2_SECRET_KEY", "AWS_SECRET_ACCESS_KEY"),
    )
    r2_public_base_url: str = ""
    diagnosis_storage_prefix: str = "diagnosis/"
    diagnosis_asset_storage: Literal["local", "s3"] = "local"
    diagnosis_local_asset_dir: str = "data/generated/diagnosis"
    diagnosis_retention_days: int = Field(default=14, ge=7, le=30)
    image_upload_max_bytes: int = Field(default=5_242_880, ge=1024, le=10_485_760)
    image_max_dimension: int = Field(default=1600, ge=512, le=4096)
    image_max_pixels: int = Field(default=12_000_000, ge=1_000_000, le=40_000_000)
    image_jpeg_quality: int = Field(default=82, ge=60, le=95)
    vlm_provider: Literal["local", "openai_compatible"] = "local"
    vlm_api_key: SecretStr | None = None
    vlm_base_url: str = ""
    vlm_model: str = "automind-vision-local-v1"
    vlm_timeout_seconds: float = Field(default=30, gt=0, le=120)
    vlm_input_price_cny_per_million: float = Field(default=0, ge=0)
    vlm_output_price_cny_per_million: float = Field(default=0, ge=0)
    diagnosis_confidence_threshold: float = Field(default=0.7, ge=0, le=1)
    guest_image_daily_limit: int = Field(default=1, ge=1, le=100)
    registered_image_daily_limit: int = Field(default=5, ge=1, le=100)
    monthly_ai_budget_cny: float = Field(default=15, ge=0)
    daily_ai_budget_cny: float = Field(default=0.6, ge=0)
    guest_text_daily_limit: int = Field(default=20, ge=1, le=1000)
    registered_text_daily_limit: int = Field(default=100, ge=1, le=10000)
    usage_quota_enabled: bool = True
    vehicle_data_provider: Literal["disabled", "nhtsa"] = "disabled"
    vehicle_data_base_url: str = "https://vpic.nhtsa.dot.gov/api"
    recall_data_base_url: str = "https://api.nhtsa.gov"
    vehicle_data_timeout_seconds: float = Field(default=8, gt=0, le=30)
    vehicle_data_cache_ttl_hours: int = Field(default=24, ge=1, le=720)
    vin_hash_secret: SecretStr | None = None
    request_timeout_seconds: float = Field(default=30, gt=0, le=120)
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = Field(default=120, ge=1, le=10000)
    redis_url: SecretStr | None = None
    redis_timeout_seconds: float = Field(default=0.5, gt=0, le=5)
    otel_enabled: bool = False
    otel_service_name: str = "automind-api"
    otel_exporter_otlp_endpoint: str = ""
    otel_exporter_otlp_headers: SecretStr | None = None
    otel_export_interval_ms: int = Field(default=60000, ge=1000, le=300000)
    budget_economy_threshold_ratio: float = Field(default=0.8, ge=0.1, le=1)
    operational_metrics_persistence_enabled: bool = True
    load_test_token: SecretStr | None = None

    @field_validator("api_v1_prefix")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        normalized = value.rstrip("/")
        if not normalized.startswith("/"):
            raise ValueError("API_V1_PREFIX must start with '/'")
        return normalized

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: object) -> object:
        if isinstance(value, SecretStr):
            value = value.get_secret_value()
        if isinstance(value, str):
            normalized = value.strip()
            if "://" in normalized:
                scheme, remainder = normalized.split("://", 1)
                if (
                    scheme == "postgres"
                    or scheme == "postgresql"
                    or scheme.startswith("postgresql+")
                ):
                    return f"postgresql+asyncpg://{remainder}"
            return normalized
        return value

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("LOG_LEVEL is invalid")
        return normalized

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @model_validator(mode="after")
    def require_product_secrets_in_production(self) -> "Settings":
        if self.app_env != "production":
            return self
        if not self.jwt_secret or len(self.jwt_secret.get_secret_value()) < 32:
            raise ValueError("JWT_SECRET must contain at least 32 characters in production")
        if not self.vin_hash_secret or len(self.vin_hash_secret.get_secret_value()) < 32:
            raise ValueError("VIN_HASH_SECRET must contain at least 32 characters in production")
        if self.rate_limit_enabled and (
            not self.redis_url or not self.redis_url.get_secret_value()
        ):
            raise ValueError("REDIS_URL is required when rate limiting is enabled in production")
        origins = self.cors_origin_list
        if (
            not origins
            or "*" in origins
            or any(not origin.startswith("https://") for origin in origins)
        ):
            raise ValueError("Production CORS_ORIGINS must contain explicit HTTPS origins")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
