import pytest
from pydantic import ValidationError

from apps.api.core.config import Settings


def test_cors_origins_are_parsed() -> None:
    settings = Settings(cors_origins="https://app.example.com, https://admin.example.com")
    assert settings.cors_origin_list == [
        "https://app.example.com",
        "https://admin.example.com",
    ]


def test_invalid_api_prefix_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(api_v1_prefix="api/v1")


def test_supabase_postgresql_url_uses_async_driver() -> None:
    settings = Settings(database_url="postgresql://user:pass@db.example.com:5432/automind")
    assert settings.database_url.get_secret_value().startswith("postgresql+asyncpg://")


def test_product_secrets_are_required_in_production() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="production", jwt_secret="", vin_hash_secret="")

    settings = Settings(
        app_env="production",
        jwt_secret="production-jwt-secret-with-32-bytes",
        vin_hash_secret="production-vin-secret-with-32-bytes",
        redis_url="redis://redis:6379/0",
        cors_origins="https://app.example.com",
    )
    assert settings.app_env == "production"

    with pytest.raises(ValidationError):
        Settings(
            app_env="production",
            jwt_secret="too-short",
            vin_hash_secret="also-too-short",
            redis_url="redis://redis:6379/0",
            cors_origins="https://app.example.com",
        )
