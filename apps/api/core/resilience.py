import asyncio
from collections.abc import Awaitable, Callable
from time import monotonic
from typing import TypeVar

T = TypeVar("T")


class CircuitOpenError(RuntimeError):
    pass


class CircuitBreaker:
    def __init__(self, *, failure_threshold: int = 3, recovery_seconds: float = 30) -> None:
        self._threshold = failure_threshold
        self._recovery_seconds = recovery_seconds
        self._failures = 0
        self._opened_at: float | None = None
        self._lock = asyncio.Lock()

    @property
    def state(self) -> str:
        if self._opened_at is None:
            return "closed"
        return "half_open" if monotonic() - self._opened_at >= self._recovery_seconds else "open"

    async def call(self, operation: Callable[[], Awaitable[T]]) -> T:
        async with self._lock:
            if self.state == "open":
                raise CircuitOpenError("Provider circuit is open")
        try:
            result = await operation()
        except Exception:
            async with self._lock:
                self._failures += 1
                if self._failures >= self._threshold:
                    self._opened_at = monotonic()
            raise
        async with self._lock:
            self._failures = 0
            self._opened_at = None
        return result
