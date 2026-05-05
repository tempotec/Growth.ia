"""Small observability helpers for local development."""

from __future__ import annotations

import logging
from contextvars import ContextVar
from time import perf_counter
from uuid import uuid4

REQUEST_ID_CTX: ContextVar[str | None] = ContextVar("request_id", default=None)
DEFAULT_LOG_LEVEL = logging.INFO


def configure_logging(level: int = DEFAULT_LOG_LEVEL) -> None:
    """Configure application logging once for local development."""

    root_logger = logging.getLogger()
    if root_logger.handlers:
        root_logger.setLevel(level)
        return

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger instance."""

    configure_logging()
    return logging.getLogger(name)


def generate_request_id() -> str:
    """Generate a short request identifier."""

    return uuid4().hex[:12]


def set_request_id(request_id: str) -> None:
    """Store the current request id in context."""

    REQUEST_ID_CTX.set(request_id)


def get_request_id() -> str | None:
    """Return the current request id, if any."""

    return REQUEST_ID_CTX.get()


def clear_request_id() -> None:
    """Clear the current request id from context."""

    REQUEST_ID_CTX.set(None)


def build_log_message(event: str, **fields: object) -> str:
    """Build a compact key=value log line."""

    payload = {"event": event}
    request_id = get_request_id()
    if request_id:
        payload["request_id"] = request_id
    payload.update({key: value for key, value in fields.items() if value is not None})
    return " ".join(f"{key}={_normalize_value(value)}" for key, value in payload.items())


def log_event(logger: logging.Logger, level: int, event: str, **fields: object) -> None:
    """Emit a structured log line."""

    logger.log(level, build_log_message(event, **fields))


def short_text(value: str | None, limit: int = 120) -> str | None:
    """Return a short, single-line representation of a text field."""

    if value is None:
        return None
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit]}..."


def start_timer() -> float:
    """Return a high-resolution timer start point."""

    return perf_counter()


def elapsed_ms(start_time: float) -> float:
    """Return elapsed milliseconds since the provided start point."""

    return round((perf_counter() - start_time) * 1000, 2)


def _normalize_value(value: object) -> str:
    """Normalize log field values to short strings."""

    if isinstance(value, float):
        return f"{value:.2f}"
    if isinstance(value, (dict, list, tuple, set)):
        return short_text(str(value), limit=160) or ""
    return str(value)
