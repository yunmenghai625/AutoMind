from contextvars import ContextVar

request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)
trace_id_context: ContextVar[str | None] = ContextVar("trace_id", default=None)
run_id_context: ContextVar[str | None] = ContextVar("run_id", default=None)
traffic_class_context: ContextVar[str] = ContextVar("traffic_class", default="user")
