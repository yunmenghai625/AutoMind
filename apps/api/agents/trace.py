from typing import Any, Protocol
from uuid import UUID


class AgentTraceStore(Protocol):
    async def create_run(
        self,
        *,
        request_id: str,
        conversation_id: UUID | None,
        input_text: str,
        agent_name: str,
    ) -> UUID: ...

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
    ) -> None: ...

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
    ) -> None: ...

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
    ) -> None: ...
