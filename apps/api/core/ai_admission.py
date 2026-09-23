import asyncio
from dataclasses import dataclass
from time import time
from uuid import uuid4

from redis.asyncio import Redis


class AiCapacityExceededError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class AiLease:
    token: str
    backend: str


class AiAdmissionController:
    """Distributed best-effort concurrency limiter with a process-local fallback."""

    _ACQUIRE_SCRIPT = """
local now = tonumber(ARGV[1])
local expires = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local token = ARGV[4]
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now)
if redis.call('ZCARD', KEYS[1]) >= limit then return 0 end
redis.call('ZADD', KEYS[1], expires, token)
redis.call('PEXPIRE', KEYS[1], math.max(1000, expires - now))
return 1
"""

    def __init__(
        self,
        *,
        url: str,
        limit: int,
        lease_seconds: int,
        timeout_seconds: float,
        fail_closed: bool = False,
        namespace: str = "default",
    ) -> None:
        self._limit = limit
        self._lease_ms = lease_seconds * 1000
        self._fail_closed = fail_closed
        self._control_key = f"automind:ai:{namespace}:enabled"
        self._concurrency_key = f"automind:ai:{namespace}:concurrency"
        self._redis = (
            Redis.from_url(
                url,
                socket_connect_timeout=timeout_seconds,
                socket_timeout=timeout_seconds,
                decode_responses=True,
            )
            if url
            else None
        )
        self._local_tokens: set[str] = set()
        self._local_enabled = True
        self._lock = asyncio.Lock()
        self.backend = "redis" if self._redis else "memory"

    async def is_enabled(self) -> bool:
        if self._redis is not None:
            try:
                value = await self._redis.get(self._control_key)
                self.backend = "redis"
                if value is not None:
                    self._local_enabled = value == "1"
            except Exception:
                self.backend = "memory-fallback"
                if self._fail_closed:
                    return False
        return self._local_enabled

    async def set_enabled(self, enabled: bool) -> bool:
        self._local_enabled = enabled
        if self._redis is not None:
            try:
                await self._redis.set(self._control_key, "1" if enabled else "0")
                self.backend = "redis"
            except Exception:
                self.backend = "memory-fallback"
                if self._fail_closed and enabled:
                    return False
        return self._local_enabled

    async def acquire(self) -> AiLease:
        token = uuid4().hex
        if self._redis is not None:
            try:
                now_ms = round(time() * 1000)
                allowed = await self._redis.eval(
                    self._ACQUIRE_SCRIPT,
                    1,
                    self._concurrency_key,
                    now_ms,
                    now_ms + self._lease_ms,
                    self._limit,
                    token,
                )
                self.backend = "redis"
                if int(allowed) != 1:
                    raise AiCapacityExceededError("AI concurrency limit reached")
                return AiLease(token=token, backend="redis")
            except AiCapacityExceededError:
                raise
            except Exception as exc:
                self.backend = "memory-fallback"
                if self._fail_closed:
                    raise AiCapacityExceededError("AI admission backend is unavailable") from exc

        async with self._lock:
            if len(self._local_tokens) >= self._limit:
                raise AiCapacityExceededError("AI concurrency limit reached")
            self._local_tokens.add(token)
        return AiLease(token=token, backend="memory")

    async def release(self, lease: AiLease) -> None:
        if lease.backend == "redis" and self._redis is not None:
            try:
                await self._redis.zrem(self._concurrency_key, lease.token)
                return
            except Exception:
                pass
        async with self._lock:
            self._local_tokens.discard(lease.token)

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()

    async def health(self) -> bool:
        if self._redis is None:
            return False
        try:
            return bool(await self._redis.ping())
        except Exception:
            return False

    @property
    def configured(self) -> bool:
        return self._redis is not None
