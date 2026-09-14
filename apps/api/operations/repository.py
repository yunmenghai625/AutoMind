from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import case, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.infrastructure.models import (
    AgentRunRecord,
    AigcGenerationRecord,
    DiagnosisRecord,
    HttpRequestMetricRecord,
    RagQueryRecord,
    ToolCallRecord,
    UsageDailyRecord,
    UserRecord,
)


class OperationalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record_http(
        self,
        *,
        request_id: str,
        trace_id: str,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        error_code: str | None,
        traffic_class: str,
    ) -> None:
        statement = (
            insert(HttpRequestMetricRecord)
            .values(
                id=uuid4(),
                request_id=request_id,
                trace_id=trace_id,
                method=method,
                path=path[:255],
                status_code=status_code,
                duration_ms=duration_ms,
                error_code=error_code,
                traffic_class=traffic_class,
            )
            .on_conflict_do_nothing(index_elements=[HttpRequestMetricRecord.request_id])
        )
        async with self._session.begin():
            await self._session.execute(statement)

    async def daily_cost(self, day: date | None = None) -> float:
        target = day or date.today()
        start = datetime.combine(target, datetime.min.time(), tzinfo=UTC)
        end = start + timedelta(days=1)
        values = []
        async with self._session.begin():
            for model in (AgentRunRecord, AigcGenerationRecord, DiagnosisRecord):
                column = model.created_at
                values.append(
                    await self._session.scalar(
                        select(func.coalesce(func.sum(model.cost_est_cny), 0)).where(
                            column >= start,
                            column < end,
                            *(
                                (AgentRunRecord.traffic_class == "user",)
                                if model is AgentRunRecord
                                else ()
                            ),
                        )
                    )
                )
        return float(sum(Decimal(str(value or 0)) for value in values))

    async def overview(self) -> dict[str, Any]:
        daily_cost = await self.daily_cost()
        since = datetime.now(UTC) - timedelta(hours=24)
        users = await self._session.scalar(select(func.count()).select_from(UserRecord))
        requests = await self._session.scalar(
            select(func.count())
            .select_from(HttpRequestMetricRecord)
            .where(
                HttpRequestMetricRecord.created_at >= since,
                HttpRequestMetricRecord.traffic_class == "user",
            )
        )
        test_requests = await self._session.scalar(
            select(func.count())
            .select_from(HttpRequestMetricRecord)
            .where(
                HttpRequestMetricRecord.created_at >= since,
                HttpRequestMetricRecord.traffic_class == "load_test",
            )
        )
        agent_total, agent_success, p95 = (
            await self._session.execute(
                select(
                    func.count(AgentRunRecord.id),
                    func.sum(case((AgentRunRecord.status == "success", 1), else_=0)),
                    func.percentile_cont(0.95).within_group(AgentRunRecord.latency_ms),
                ).where(
                    AgentRunRecord.created_at >= since,
                    AgentRunRecord.traffic_class == "user",
                )
            )
        ).one()
        tool_total, tool_success = (
            await self._session.execute(
                select(
                    func.count(ToolCallRecord.id),
                    func.sum(case((ToolCallRecord.status == "success", 1), else_=0)),
                )
                .join(AgentRunRecord, AgentRunRecord.id == ToolCallRecord.run_id)
                .where(
                    ToolCallRecord.created_at >= since,
                    AgentRunRecord.traffic_class == "user",
                )
            )
        ).one()
        return {
            "users": int(users or 0),
            "requests": int(requests or 0),
            "testRequests": int(test_requests or 0),
            "agentSuccessRate": _percent(agent_success, agent_total),
            "p95Latency": round(float(p95 or 0) / 1000, 3),
            "toolSuccessRate": _percent(tool_success, tool_total),
            "aiCost": round(daily_cost, 6),
            "generatedAt": datetime.now(UTC).isoformat(),
        }

    async def daily_metrics(self, since: date) -> dict[str, list[dict[str, Any]]]:
        start = datetime.combine(since, datetime.min.time(), tzinfo=UTC)
        http_rows = (
            await self._session.execute(
                select(
                    func.date(HttpRequestMetricRecord.created_at),
                    HttpRequestMetricRecord.traffic_class,
                    func.count(HttpRequestMetricRecord.id),
                )
                .where(HttpRequestMetricRecord.created_at >= start)
                .group_by(
                    func.date(HttpRequestMetricRecord.created_at),
                    HttpRequestMetricRecord.traffic_class,
                )
            )
        ).all()
        agent_rows = (
            await self._session.execute(
                select(
                    func.date(AgentRunRecord.created_at),
                    func.count(AgentRunRecord.id),
                    func.sum(case((AgentRunRecord.status == "success", 1), else_=0)),
                    func.percentile_cont(0.5).within_group(AgentRunRecord.latency_ms),
                    func.percentile_cont(0.95).within_group(AgentRunRecord.latency_ms),
                    func.percentile_cont(0.99).within_group(AgentRunRecord.latency_ms),
                    func.sum(AgentRunRecord.cost_est_cny),
                )
                .where(AgentRunRecord.created_at >= start)
                .where(AgentRunRecord.traffic_class == "user")
                .group_by(func.date(AgentRunRecord.created_at))
            )
        ).all()
        usage_rows = (
            await self._session.execute(
                select(AgentRunRecord.agent_name, func.count(AgentRunRecord.id))
                .where(AgentRunRecord.created_at >= start)
                .where(AgentRunRecord.traffic_class == "user")
                .group_by(AgentRunRecord.agent_name)
            )
        ).all()
        extra_cost_rows = (
            await self._session.execute(
                select(
                    func.date(UsageDailyRecord.date),
                    func.sum(UsageDailyRecord.cost_est_cny),
                )
                .where(UsageDailyRecord.date >= since)
                .group_by(UsageDailyRecord.date)
            )
        ).all()
        return {
            "http": _traffic_rows(http_rows),
            "agents": [
                {
                    "date": row[0],
                    "total": int(row[1]),
                    "success": int(row[2] or 0),
                    "p50": float(row[3] or 0),
                    "p95": float(row[4] or 0),
                    "p99": float(row[5] or 0),
                    "cost": float(row[6] or 0),
                }
                for row in agent_rows
            ],
            "usage": [{"agent": row[0], "calls": int(row[1])} for row in usage_rows],
            "extra_cost": [{"date": row[0], "cost": float(row[1] or 0)} for row in extra_cost_rows],
        }

    async def operational_totals(self) -> dict[str, Any]:
        agent = (
            await self._session.execute(
                select(
                    func.count(AgentRunRecord.id),
                    func.sum(AgentRunRecord.token_in),
                    func.sum(AgentRunRecord.token_out),
                    func.sum(AgentRunRecord.cost_est_cny),
                    func.avg(AgentRunRecord.latency_ms),
                ).where(AgentRunRecord.traffic_class == "user")
            )
        ).one()
        tool = (
            await self._session.execute(
                select(func.count(ToolCallRecord.id), func.avg(ToolCallRecord.latency_ms))
                .join(AgentRunRecord, AgentRunRecord.id == ToolCallRecord.run_id)
                .where(AgentRunRecord.traffic_class == "user")
            )
        ).one()
        rag = (
            await self._session.execute(
                select(
                    func.count(RagQueryRecord.id),
                    func.avg(RagQueryRecord.vector_search_ms),
                    func.avg(RagQueryRecord.rerank_ms),
                ).where(RagQueryRecord.traffic_class == "user")
            )
        ).one()
        return {
            "agent": {
                "calls": int(agent[0] or 0),
                "tokenIn": int(agent[1] or 0),
                "tokenOut": int(agent[2] or 0),
                "costCny": float(agent[3] or 0),
                "avgLatencyMs": round(float(agent[4] or 0), 2),
            },
            "tool": {"calls": int(tool[0] or 0), "avgLatencyMs": round(float(tool[1] or 0), 2)},
            "rag": {
                "queries": int(rag[0] or 0),
                "avgVectorMs": round(float(rag[1] or 0), 2),
                "avgRerankMs": round(float(rag[2] or 0), 2),
            },
        }

    async def safety_events(self, limit: int = 20) -> list[dict[str, Any]]:
        rows = (
            await self._session.scalars(
                select(ToolCallRecord)
                .where(ToolCallRecord.safety_decision == "rejected")
                .order_by(ToolCallRecord.created_at.desc())
                .limit(limit)
            )
        ).all()
        return [
            {
                "id": str(row.id),
                "rule": row.safety_code or "SAFETY_REJECTED",
                "severity": "blocked",
                "message": f"{row.tool_name} rejected by SafetyPolicyEngine",
                "at": row.created_at.isoformat(),
            }
            for row in rows
        ]

    async def request_by_id(self, request_id: str) -> dict[str, Any] | None:
        row = await self._session.scalar(
            select(HttpRequestMetricRecord).where(HttpRequestMetricRecord.request_id == request_id)
        )
        if row is None:
            return None
        return {
            "requestId": row.request_id,
            "traceId": row.trace_id,
            "method": row.method,
            "path": row.path,
            "statusCode": row.status_code,
            "durationMs": row.duration_ms,
            "errorCode": row.error_code,
            "trafficClass": row.traffic_class,
            "createdAt": row.created_at.isoformat(),
        }


def _percent(numerator: Any, denominator: Any) -> float:
    return round(float(numerator or 0) * 100 / float(denominator), 2) if denominator else 0.0


def _traffic_rows(rows: list[Any]) -> list[dict[str, Any]]:
    daily: dict[date, dict[str, Any]] = {}
    for day, traffic_class, count in rows:
        item = daily.setdefault(day, {"date": day, "requests": 0, "test_requests": 0})
        key = "test_requests" if traffic_class == "load_test" else "requests"
        item[key] += int(count)
    return list(daily.values())
