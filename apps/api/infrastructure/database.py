import asyncio
from functools import lru_cache

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from apps.api.core.config import Settings, get_settings
from apps.api.schemas.health import DependencyHealth

_engines: set[AsyncEngine] = set()


@lru_cache
def get_engine(database_url: str | None = None) -> AsyncEngine:
    url = database_url or get_settings().database_url.get_secret_value()
    engine = create_async_engine(url, pool_pre_ping=True)
    _engines.add(engine)
    return engine


def get_session_factory(settings: Settings | None = None) -> async_sessionmaker[AsyncSession]:
    resolved = settings or get_settings()
    engine = get_engine(resolved.database_url.get_secret_value())
    return async_sessionmaker(engine, expire_on_commit=False)


async def check_database(settings: Settings) -> DependencyHealth:
    if not settings.database_healthcheck_enabled:
        return DependencyHealth(status="disabled")

    try:
        engine = get_engine(settings.database_url.get_secret_value())
        async with asyncio.timeout(settings.database_connect_timeout_seconds):
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        return DependencyHealth(status="ok")
    except Exception as exc:
        return DependencyHealth(status="unavailable", detail=type(exc).__name__)


async def close_database() -> None:
    for engine in tuple(_engines):
        await engine.dispose()
    _engines.clear()
    get_engine.cache_clear()
