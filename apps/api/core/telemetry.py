import logging
from contextlib import AbstractContextManager, suppress
from typing import Any

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from apps.api.core.config import Settings
from apps.api.core.logging import JsonFormatter
from apps.api.core.request_context import traffic_class_context

_configured = False
_operation_count = None
_operation_latency = None
_token_count = None
_cost_count = None
_trace_provider = None
_meter_provider = None
_logger_provider = None


class _SanitizedOtelHandler(logging.Handler):
    """Forward the already-redacted JSON representation to OTLP logs."""

    def __init__(self, target: LoggingHandler) -> None:
        super().__init__()
        self._target = target
        self._formatter = JsonFormatter()

    def emit(self, record: logging.LogRecord) -> None:
        if record.name.startswith("opentelemetry"):
            return
        try:
            safe_record = logging.LogRecord(
                name=record.name,
                level=record.levelno,
                pathname="",
                lineno=0,
                msg=self._formatter.format(record),
                args=(),
                exc_info=None,
            )
            safe_record.created = record.created
            self._target.emit(safe_record)
        except Exception:
            self.handleError(record)


def configure_telemetry(settings: Settings) -> None:
    global _configured, _operation_count, _operation_latency, _token_count, _cost_count
    global _trace_provider, _meter_provider, _logger_provider
    if _configured or not settings.otel_enabled:
        return
    resource = Resource.create(
        {SERVICE_NAME: settings.otel_service_name, SERVICE_VERSION: settings.app_version}
    )
    trace_provider = TracerProvider(resource=resource)
    metric_readers = []
    endpoint = settings.otel_exporter_otlp_endpoint.rstrip("/")
    headers = _headers(settings)
    if endpoint:
        trace_provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces", headers=headers))
        )
        metric_readers.append(
            PeriodicExportingMetricReader(
                OTLPMetricExporter(endpoint=f"{endpoint}/v1/metrics", headers=headers),
                export_interval_millis=settings.otel_export_interval_ms,
            )
        )
        logger_provider = LoggerProvider(resource=resource)
        logger_provider.add_log_record_processor(
            BatchLogRecordProcessor(
                OTLPLogExporter(endpoint=f"{endpoint}/v1/logs", headers=headers)
            )
        )
        logging.getLogger().addHandler(
            _SanitizedOtelHandler(LoggingHandler(logger_provider=logger_provider))
        )
        _logger_provider = logger_provider
    trace.set_tracer_provider(trace_provider)
    meter_provider = MeterProvider(resource=resource, metric_readers=metric_readers)
    metrics.set_meter_provider(meter_provider)
    meter = metrics.get_meter(settings.otel_service_name, settings.app_version)
    _operation_count = meter.create_counter("automind.operation.count")
    _operation_latency = meter.create_histogram("automind.operation.duration", unit="ms")
    _token_count = meter.create_counter("automind.llm.tokens")
    _cost_count = meter.create_counter("automind.ai.cost", unit="CNY")
    _trace_provider = trace_provider
    _meter_provider = meter_provider
    _configured = True


def shutdown_telemetry() -> None:
    """Flush telemetry during graceful process shutdown."""
    for provider in (_logger_provider, _meter_provider, _trace_provider):
        if provider is not None:
            with suppress(Exception):
                provider.shutdown()


def span(name: str, attributes: dict[str, Any] | None = None) -> AbstractContextManager[Any]:
    return trace.get_tracer("automind").start_as_current_span(name, attributes=attributes or {})


def current_trace_id() -> str | None:
    context = trace.get_current_span().get_span_context()
    return f"{context.trace_id:032x}" if context.is_valid else None


def record_operation(
    kind: str,
    *,
    status: str,
    latency_ms: float,
    tokens_in: int = 0,
    tokens_out: int = 0,
    cost_cny: float = 0,
    name: str | None = None,
) -> None:
    attributes = {"operation.kind": kind, "operation.status": status}
    attributes["traffic.class"] = traffic_class_context.get()
    if name:
        attributes["operation.name"] = name
    if _operation_count is not None:
        _operation_count.add(1, attributes)
        _operation_latency.record(latency_ms, attributes)
        if tokens_in:
            _token_count.add(tokens_in, {**attributes, "token.type": "input"})
        if tokens_out:
            _token_count.add(tokens_out, {**attributes, "token.type": "output"})
        if cost_cny:
            _cost_count.add(cost_cny, attributes)


def _headers(settings: Settings) -> dict[str, str]:
    raw = (
        settings.otel_exporter_otlp_headers.get_secret_value()
        if settings.otel_exporter_otlp_headers
        else ""
    )
    pairs = (item.partition("=") for item in raw.split(","))
    return {
        key.strip(): value.strip() for key, separator, value in pairs if separator and key.strip()
    }
