import pytest
from pydantic import SecretStr, ValidationError

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


def test_railway_postgres_url_uses_async_driver() -> None:
    settings = Settings(database_url="postgres://user:pass@db.example.com:5432/automind")
    assert settings.database_url.get_secret_value().startswith("postgresql+asyncpg://")


def test_postgres_driver_url_is_forced_to_installed_asyncpg_driver() -> None:
    settings = Settings(
        database_url="  postgresql+psycopg://user:pass@db.example.com:5432/automind  "
    )
    assert (
        settings.database_url.get_secret_value()
        == "postgresql+asyncpg://user:pass@db.example.com:5432/automind"
    )


def test_secret_postgres_url_uses_async_driver() -> None:
    settings = Settings(
        database_url=SecretStr("postgresql://user:pass@db.example.com:5432/automind")
    )
    assert settings.database_url.get_secret_value().startswith("postgresql+asyncpg://")


def test_railway_bucket_aws_variables_are_supported() -> None:
    settings = Settings(
        AWS_ENDPOINT_URL="https://t3.storageapi.dev",
        AWS_S3_BUCKET_NAME="automind-assets-example",
        AWS_ACCESS_KEY_ID="access-key",
        AWS_SECRET_ACCESS_KEY="secret-key",
    )

    assert settings.r2_endpoint == "https://t3.storageapi.dev"
    assert settings.r2_bucket == "automind-assets-example"
    assert settings.r2_access_key is not None
    assert settings.r2_access_key.get_secret_value() == "access-key"
    assert settings.r2_secret_key is not None
    assert settings.r2_secret_key.get_secret_value() == "secret-key"


def test_product_secrets_are_required_in_production() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="production", jwt_secret="", vin_hash_secret="")

    settings = Settings(
        app_env="production",
        jwt_secret="production-jwt-secret-with-32-bytes",
        vin_hash_secret="production-vin-secret-with-32-bytes",
        admin_password_hash="pbkdf2_sha256$600000$test$test",
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

    with pytest.raises(ValidationError):
        Settings(
            app_env="production",
            jwt_secret="production-jwt-secret-with-32-bytes",
            vin_hash_secret="production-vin-secret-with-32-bytes",
            admin_password_hash="pbkdf2_sha256$600000$test$test",
            redis_url="redis://redis:6379/0",
            cors_origins="https://app.example.com",
            rate_limit_enabled=False,
        )
