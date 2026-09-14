from dataclasses import asdict, dataclass
from datetime import date, timedelta
from typing import Any

from apps.api.operations.repository import OperationalRepository


@dataclass(frozen=True, slots=True)
class BudgetState:
    state: str
    spent_cny: float
    limit_cny: float
    threshold_ratio: float


class BudgetGuard:
    def __init__(
        self, repository: OperationalRepository, *, daily_limit: float, economy_ratio: float
    ) -> None:
        self._repository = repository
        self._limit = daily_limit
        self._economy_ratio = economy_ratio

    async def current(self) -> BudgetState:
        spent = await self._repository.daily_cost()
        if self._limit <= 0 or spent >= self._limit:
            state = "exhausted"
        elif spent >= self._limit * self._economy_ratio:
            state = "economy"
        else:
            state = "normal"
        return BudgetState(state, round(spent, 6), self._limit, self._economy_ratio)

    async def as_dict(self) -> dict[str, Any]:
        return asdict(await self.current())


class AdminMetricsService:
    def __init__(self, repository: OperationalRepository) -> None:
        self._repository = repository

    async def metrics(self, days: int = 14) -> dict[str, Any]:
        start = date.today() - timedelta(days=days - 1)
        raw = await self._repository.daily_metrics(start)
        http = {row["date"]: row for row in raw["http"]}
        agents = {row["date"]: row for row in raw["agents"]}
        extra_cost = {row["date"]: row for row in raw["extra_cost"]}
        traffic, latency, daily_cost = [], [], []
        for offset in range(days):
            day = start + timedelta(days=offset)
            agent = agents.get(day, {})
            total = int(agent.get("total", 0))
            traffic.append(
                {
                    "timestamp": day.isoformat(),
                    "requests": int(http.get(day, {}).get("requests", 0)),
                    "testRequests": int(http.get(day, {}).get("test_requests", 0)),
                    "agentSuccessRate": round(int(agent.get("success", 0)) * 100 / total, 2)
                    if total
                    else 0,
                }
            )
            latency.append(
                {
                    "date": day.strftime("%m-%d"),
                    "p50": round(float(agent.get("p50", 0)) / 1000, 3),
                    "p95": round(float(agent.get("p95", 0)) / 1000, 3),
                    "p99": round(float(agent.get("p99", 0)) / 1000, 3),
                }
            )
            daily_cost.append(
                {
                    "date": day.strftime("%m-%d"),
                    "cost": round(
                        float(agent.get("cost", 0)) + float(extra_cost.get(day, {}).get("cost", 0)),
                        6,
                    ),
                }
            )
        return {
            "traffic": traffic,
            "usage": raw["usage"],
            "dailyCost": daily_cost,
            "latency": latency,
        }
