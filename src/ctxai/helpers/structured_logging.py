"""Structured JSON logging with correlation IDs for CtxAI.

Provides a Python logging handler that emits JSON-formatted log lines
suitable for log aggregators (Datadog, ELK, Loki, etc.).

Each log entry includes:
  - timestamp (ISO 8601 with UTC timezone)
  - level
  - message
  - trace_id (correlation ID from AgentContext)
  - context_id (AgentContext ID when available)
  - agent_name (AgentContext name when available)
  - logger (source logger name)

Usage:
    from ctxai.helpers.structured_logging import setup_structured_logging

    # Call once at application startup
    setup_structured_logging()

    # Use standard Python logging
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Server started", extra={"port": 50001})

    # Or emit with context binding
    from ctxai.helpers.structured_logging import get_logger, bind_context
    logger = get_logger(__name__)
    with bind_context(context_id="abc123", trace_id="xyz789"):
        logger.info("Processing request")
"""

from __future__ import annotations

import contextvars
import json
import logging
import sys
import threading
from datetime import UTC, datetime
from typing import Any

# ---------------------------------------------------------------------------
# Context-var based correlation IDs
# ---------------------------------------------------------------------------
_trace_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="")
_context_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("context_id", default="")
_agent_name_var: contextvars.ContextVar[str] = contextvars.ContextVar("agent_name", default="")


def get_trace_id() -> str:
    return _trace_id_var.get()


def set_trace_id(value: str) -> None:
    _trace_id_var.set(value)


def get_context_id() -> str:
    return _context_id_var.get()


def set_context_id(value: str) -> None:
    _context_id_var.set(value)


def get_agent_name() -> str:
    return _agent_name_var.get()


def set_agent_name(value: str) -> None:
    _agent_name_var.set(value)


class bind_context:
    """Context manager that temporarily binds correlation IDs to log entries.

    Usage:
        with bind_context(context_id="ctx-123", trace_id="trace-456", agent_name="my-agent"):
            logger.info("doing work")
    """

    def __init__(
        self,
        *,
        context_id: str = "",
        trace_id: str = "",
        agent_name: str = "",
    ) -> None:
        self._context_id = context_id
        self._trace_id = trace_id
        self._agent_name = agent_name
        self._tokens: list[contextvars.Token[str]] = []

    def __enter__(self) -> bind_context:
        if self._context_id:
            self._tokens.append(_context_id_var.set(self._context_id))
        if self._trace_id:
            self._tokens.append(_trace_id_var.set(self._trace_id))
        if self._agent_name:
            self._tokens.append(_agent_name_var.set(self._agent_name))
        return self

    def __exit__(self, *_: Any) -> None:
        for token in reversed(self._tokens):
            token.var.reset(token)


# ---------------------------------------------------------------------------
# JSON formatter
# ---------------------------------------------------------------------------
class StructuredJsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def __init__(self, *, include_extra: bool = True) -> None:
        super().__init__()
        self.include_extra = include_extra

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Correlation IDs from context vars (may be empty)
        trace_id = get_trace_id() or getattr(record, "trace_id", "")

        # Fall back to OpenTelemetry trace ID if no explicit trace_id
        if not trace_id:
            try:
                from opentelemetry import trace as otel_trace

                span = otel_trace.get_current_span()
                ctx = span.get_span_context()
                if ctx and ctx.trace_id:
                    trace_id = format(ctx.trace_id, "032x")
            except Exception:
                pass

        context_id = get_context_id() or getattr(record, "context_id", "")
        agent_name = get_agent_name() or getattr(record, "agent_name", "")

        if trace_id:
            entry["trace_id"] = trace_id
        if context_id:
            entry["context_id"] = context_id
        if agent_name:
            entry["agent_name"] = agent_name

        # Include extra fields passed via logger.info("msg", extra={"key": val})
        if self.include_extra:
            standard_keys = {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "message",
                "trace_id",
                "context_id",
                "agent_name",
            }
            extra = {k: v for k, v in record.__dict__.items() if k not in standard_keys and not k.startswith("_")}
            if extra:
                entry["extra"] = extra

        # Exception info
        if record.exc_info and record.exc_info[0] is not None:
            entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(entry, default=str, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Structured log handler (stdout)
# ---------------------------------------------------------------------------
class StructuredLogHandler(logging.Handler):
    """Thread-safe handler that writes JSON lines to a stream (default: stdout)."""

    def __init__(self, stream: Any = None) -> None:
        super().__init__()
        self.stream = stream or sys.stdout
        self._lock = threading.Lock()
        self.setFormatter(StructuredJsonFormatter())

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            with self._lock:
                self.stream.write(msg + "\n")
                self.stream.flush()
        except Exception:
            self.handleError(record)


# ---------------------------------------------------------------------------
# Setup helpers
# ---------------------------------------------------------------------------
def setup_structured_logging(
    *,
    level: int | str = logging.INFO,
    logger_name: str = "",
    replace_existing: bool = True,
) -> logging.Logger:
    """Configure a logger with structured JSON output to stdout.

    Args:
        level: Root log level (default INFO).
        logger_name: Target logger name. Empty string = root logger.
        replace_existing: If True, remove existing handlers first.
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)

    if replace_existing:
        logger.handlers.clear()

    handler = StructuredLogHandler()
    handler.setLevel(level)
    logger.addHandler(handler)

    # Prevent double-emission through root logger
    logger.propagate = False

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a child logger that inherits the structured handler."""
    return logging.getLogger(name)


# ---------------------------------------------------------------------------
# Convenience: emit a structured log line directly (drop-in for PrintStyle)
# ---------------------------------------------------------------------------
def log_event(
    level: str,
    message: str,
    *,
    context_id: str | None = None,
    trace_id: str | None = None,
    agent_name: str | None = None,
    **extra: Any,
) -> None:
    """Emit a single structured JSON log line to stdout.

    This is a lightweight alternative to PrintStyle.json_log with proper
    correlation-ID support and standard Python logging integration.
    """
    logger = logging.getLogger("ctxai.event")
    lvl = getattr(logging, level.upper(), logging.INFO)

    record_extra: dict[str, Any] = {}
    if context_id:
        record_extra["context_id"] = context_id
    if trace_id:
        record_extra["trace_id"] = trace_id
    if agent_name:
        record_extra["agent_name"] = agent_name
    record_extra.update(extra)

    logger.log(lvl, message, extra=record_extra)
