import asyncio
from dataclasses import dataclass
from time import monotonic

from redis.asyncio import Redis


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int


class RedisRateLimiter:
    _MAX_FALLBACK_KEYS = 10_000
    _SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
local ttl = redis.call('TTL', KEYS[1])
return {current, ttl}
"""

    def __init__(self, *, url: str, limit: int, timeout_seconds: float) -> None:
        self._limit = limit
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
        self._fallback: dict[str, tuple[int, float]] = {}
        self._lock = asyncio.Lock()
        self.backend = "redis" if self._redis else "memory"

    async def allow(self, key: str) -> RateLimitDecision:
        if self._redis is not None:
            try:
                result = await self._redis.eval(self._SCRIPT, 1, f"automind:rate:{key}", 60)
                count, ttl = int(result[0]), max(1, int(result[1]))
                self.backend = "redis"
                return self._decision(count, ttl)
            except Exception:
                self.backend = "memory-fallback"
        return await self._memory_allow(key)

    async def health(self) -> bool:
        if self._redis is None:
            return False
        try:
            return bool(await self._redis.ping())
        except Exception:
            return False

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()

    async def _memory_allow(self, key: str) -> RateLimitDecision:
        now = monotonic()
        async with self._lock:
            if key not in self._fallback and len(self._fallback) >= self._MAX_FALLBACK_KEYS:
                self._fallback = {
                    item_key: item for item_key, item in self._fallback.items() if item[1] > now
                }
                if len(self._fallback) >= self._MAX_FALLBACK_KEYS:
                    key = "overflow"
            count, expires = self._fallback.get(key, (0, now + 60))
            if now >= expires:
                count, expires = 0, now + 60
            count += 1
            self._fallback[key] = (count, expires)
        return self._decision(count, max(1, round(expires - now)))

    def _decision(self, count: int, retry_after: int) -> RateLimitDecision:
        return RateLimitDecision(
            allowed=count <= self._limit,
            limit=self._limit,
            remaining=max(0, self._limit - count),
            retry_after_seconds=retry_after,
        )
