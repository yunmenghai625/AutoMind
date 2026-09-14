from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.core.request_context import (
    run_id_context,
    trace_id_context,
    traffic_class_context,
)
from apps.api.core.telemetry import record_operation
from apps.api.infrastructure.models import AgentRunRecord, AgentStepRecord, ToolCallRecord


class PostgresAgentTraceStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_run(
        self,
        *,
        request_id: str,
        conversation_id: UUID | None,
        input_text: str,
        agent_name: str,
    ) -> UUID:
        run_id = uuid4()
        async with self._session.begin():
            self._session.add(
                AgentRunRecord(
                    id=run_id,
                    request_id=request_id,
                    trace_id=trace_id_context.get(),
                    traffic_class=traffic_class_context.get(),
                    conversation_id=conversation_id,
                    input_text=input_text,
                    agent_name=agent_name,
                    status="running",
                )
            )
        run_id_context.set(str(run_id))
        return run_id

    async def record_step(
        self,
        *,
        run_id: UUID,
        sequence: int,
        node_name: str,
        latency_ms: int,
        status: str,
        input_summary: str | None = None,
        output_summary: str | None = None,
        error_code: str | None = None,
    ) -> None:
        async with self._session.begin():
            self._session.add(
                AgentStepRecord(
                    run_id=run_id,
                    sequence=sequence,
                    node_name=node_name,
                    latency_ms=latency_ms,
                    status=status,
                    input_summary=input_summary,
                    output_summary=output_summary,
                    error_code=error_code,
                )
            )

    async def record_tool_call(
        self,
        *,
        run_id: UUID,
        tool_name: str,
        arguments: dict[str, Any],
        result: dict[str, Any] | None,
        latency_ms: int,
        status: str,
        safety_decision: str,
        safety_code: str | None,
    ) -> None:
        record_operation("tool", status=status, latency_ms=latency_ms, name=tool_name)
        async with self._session.begin():
            self._session.add(
                ToolCallRecord(
                    run_id=run_id,
                    tool_name=tool_name,
                    arguments_json=arguments,
                    result_json=result,
                    latency_ms=latency_ms,
                    status=status,
                    safety_decision=safety_decision,
                    safety_code=safety_code,
                )
            )

    async def complete_run(
        self,
        *,
        run_id: UUID,
        latency_ms: int,
        status: str,
        model: str | None,
        token_in: int,
        token_out: int,
        cost_est_cny: float,
        llm_calls: int,
        response_summary: str | None,
        error_code: str | None = None,
    ) -> None:
        record_operation(
            "agent",
            status=status,
            latency_ms=latency_ms,
            tokens_in=token_in,
            tokens_out=token_out,
            cost_cny=cost_est_cny,
            name="agent_run",
        )
        async with self._session.begin():
            await self._session.execute(
                update(AgentRunRecord)
                .where(AgentRunRecord.id == run_id)
                .values(
                    latency_ms=latency_ms,
                    status=status,
                    model=model,
                    token_in=token_in,
                    token_out=token_out,
                    cost_est_cny=cost_est_cny,
                    llm_calls=llm_calls,
                    response_summary=response_summary,
                    error_code=error_code,
                    completed_at=datetime.now(UTC),
                )
            )

    async def list_runs(self, *, limit: int = 50) -> list[dict[str, Any]]:
        steps_subquery = (
            select(AgentStepRecord.run_id, func.count(AgentStepRecord.id).label("steps"))
            .group_by(AgentStepRecord.run_id)
            .subquery()
        )
        tools_subquery = (
            select(
                ToolCallRecord.run_id,
                func.array_agg(func.distinct(ToolCallRecord.tool_name)).label("tools"),
            )
            .group_by(ToolCallRecord.run_id)
            .subquery()
        )
        statement = (
            select(AgentRunRecord, steps_subquery.c.steps, tools_subquery.c.tools)
            .outerjoin(steps_subquery, steps_subquery.c.run_id == AgentRunRecord.id)
            .outerjoin(tools_subquery, tools_subquery.c.run_id == AgentRunRecord.id)
            .order_by(AgentRunRecord.created_at.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(statement)).all()
        return [
            {
                "id": str(run.id),
                "requestId": run.request_id,
                "traceId": run.trace_id,
                "trafficClass": run.traffic_class,
                "agent": run.agent_name,
                "latencyMs": run.latency_ms,
                "steps": int(step_count or 0),
                "toolsUsed": list(tools or []),
                "status": run.status,
                "time": run.created_at.isoformat(),
            }
            for run, step_count, tools in rows
        ]

    async def get_run(self, run_id: UUID) -> dict[str, Any] | None:
        run = await self._session.get(AgentRunRecord, run_id)
        if run is None:
            return None
        steps = (
            await self._session.scalars(
                select(AgentStepRecord)
                .where(AgentStepRecord.run_id == run_id)
                .order_by(AgentStepRecord.sequence)
            )
        ).all()
        tools = (
            await self._session.scalars(
                select(ToolCallRecord)
                .where(ToolCallRecord.run_id == run_id)
                .order_by(ToolCallRecord.created_at)
            )
        ).all()
        trace = [
            {
                "name": step.node_name,
                "durationMs": step.latency_ms,
                "detail": step.output_summary or step.status,
            }
            for step in steps
        ]
        trace.extend(
            {
                "name": f"tool:{tool.tool_name}",
                "durationMs": tool.latency_ms,
                "detail": f"{tool.status} / safety={tool.safety_decision}",
            }
            for tool in tools
        )
        return {
            "id": str(run.id),
            "requestId": run.request_id,
            "traceId": run.trace_id,
            "trafficClass": run.traffic_class,
            "agent": run.agent_name,
            "latencyMs": run.latency_ms,
            "steps": len(steps),
            "toolsUsed": sorted({tool.tool_name for tool in tools}),
            "status": run.status,
            "time": run.created_at.isoformat(),
            "query": run.input_text,
            "trace": trace,
            "model": run.model,
            "llmCalls": run.llm_calls,
            "tokenIn": run.token_in,
            "tokenOut": run.token_out,
            "costEstCny": float(run.cost_est_cny or Decimal(0)),
        }
