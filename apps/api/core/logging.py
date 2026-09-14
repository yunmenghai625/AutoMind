import json
import logging
import re
from datetime import UTC, datetime

from apps.api.core.request_context import request_id_context

_STANDARD_RECORD_FIELDS = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime"}
_SENSITIVE_KEYS = ("authorization", "password", "secret", "api_key", "token", "vin")
_BEARER_PATTERN = re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]+")
_VIN_PATTERN = re.compile(r"\b[A-HJ-NPR-Z0-9]{17}\b", re.IGNORECASE)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": _scrub_text(record.getMessage()),
            "request_id": request_id_context.get(),
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD_RECORD_FIELDS and not key.startswith("_"):
                payload[key] = _sanitize(key, value)
        if record.exc_info:
            payload["exception"] = _scrub_text(self.formatException(record.exc_info))
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


def _sanitize(key: str, value: object) -> object:
    if any(fragment in key.lower() for fragment in _SENSITIVE_KEYS):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(item_key): _sanitize(str(item_key), item) for item_key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize(key, item) for item in value]
    return _scrub_text(value) if isinstance(value, str) else value


def _scrub_text(value: str) -> str:
    redacted = _BEARER_PATTERN.sub("Bearer [REDACTED]", value)
    redacted = _VIN_PATTERN.sub("[REDACTED_VIN]", redacted)
    return redacted[:4000]
