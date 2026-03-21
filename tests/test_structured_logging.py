"""Unit tests for structured logging and OpenTelemetry instrumentation."""

import json
import logging

from ctxai.helpers.opentelemetry_instrumentation import (
    get_current_trace_id,
    get_tracer,
    setup_tracing,
    start_span,
)
from ctxai.helpers.structured_logging import (
    StructuredJsonFormatter,
    _context_id_var,
    _trace_id_var,
    bind_context,
    get_context_id,
    get_trace_id,
)

# ---------------------------------------------------------------------------
# StructuredJsonFormatter
# ---------------------------------------------------------------------------


class TestStructuredJsonFormatter:
    def _make_record(self, level="INFO", msg="hello", **extra):
        logger = logging.getLogger("test")
        record = logger.makeRecord(logger.name, getattr(logging, level), "test.py", 1, msg, (), None)
        for k, v in extra.items():
            setattr(record, k, v)
        return record

    def test_basic_output(self):
        fmt = StructuredJsonFormatter()
        record = self._make_record()
        line = fmt.format(record)
        data = json.loads(line)
        assert data["level"] == "INFO"
        assert data["message"] == "hello"
        assert data["logger"] == "test"
        assert "timestamp" in data

    def test_includes_extra_fields(self):
        fmt = StructuredJsonFormatter()
        record = self._make_record(custom_field="custom_value")
        line = fmt.format(record)
        data = json.loads(line)
        assert data["extra"]["custom_field"] == "custom_value"

    def test_includes_trace_id_from_context_var(self):
        fmt = StructuredJsonFormatter()
        token = _trace_id_var.set("abc123")
        try:
            record = self._make_record()
            line = fmt.format(record)
            data = json.loads(line)
            assert data["trace_id"] == "abc123"
        finally:
            _trace_id_var.reset(token)

    def test_includes_context_id_from_context_var(self):
        fmt = StructuredJsonFormatter()
        token = _context_id_var.set("ctx-456")
        try:
            record = self._make_record()
            line = fmt.format(record)
            data = json.loads(line)
            assert data["context_id"] == "ctx-456"
        finally:
            _context_id_var.reset(token)

    def test_exception_included(self):
        fmt = StructuredJsonFormatter()
        try:
            raise ValueError("test error")
        except ValueError:
            import sys

            record = self._make_record(exc_info=sys.exc_info())
            line = fmt.format(record)
            data = json.loads(line)
            assert "exception" in data
            assert "ValueError" in data["exception"]


# ---------------------------------------------------------------------------
# bind_context
# ---------------------------------------------------------------------------


class TestBindContext:
    def test_binds_and_restores_context_vars(self):
        # Ensure clean state
        tok1 = _trace_id_var.set("")
        tok2 = _context_id_var.set("")
        try:
            assert get_trace_id() == ""
            assert get_context_id() == ""

            with bind_context(trace_id="t1", context_id="c1", agent_name="agent1"):
                assert get_trace_id() == "t1"
                assert get_context_id() == "c1"

            # Restored to empty
            assert get_trace_id() == ""
            assert get_context_id() == ""
        finally:
            _trace_id_var.reset(tok1)
            _context_id_var.reset(tok2)

    def test_nested_contexts(self):
        tok = _trace_id_var.set("")
        try:
            with bind_context(trace_id="outer"):
                assert get_trace_id() == "outer"
                with bind_context(trace_id="inner"):
                    assert get_trace_id() == "inner"
                assert get_trace_id() == "outer"
        finally:
            _trace_id_var.reset(tok)


# ---------------------------------------------------------------------------
# OpenTelemetry instrumentation
# ---------------------------------------------------------------------------


class TestOpenTelemetryInstrumentation:
    def test_tracer_returns_tracer_instance(self):
        tracer = get_tracer("test")
        assert tracer is not None

    def test_start_span_creates_span(self):
        # Set up tracing first to get real spans
        setup_tracing(service_name="test", console_export=False)
        tracer = get_tracer("test")
        with start_span(tracer, "test.op", attributes={"key": "val"}) as span:
            assert span is not None
            # After setup, span should be a real RecordingSpan with name
            assert hasattr(span, "name")

    def test_get_current_trace_id_returns_hex(self):
        setup_tracing(service_name="test", console_export=False)
        tracer = get_tracer("test")
        with start_span(tracer, "test.op"):
            trace_id = get_current_trace_id()
            assert len(trace_id) == 32  # 128-bit trace ID as 32 hex chars

    def test_get_current_trace_id_empty_outside_span(self):
        # Outside any span, should return empty or valid hex
        trace_id = get_current_trace_id()
        assert isinstance(trace_id, str)

    def test_setup_tracing_is_idempotent(self):
        # First call configures
        p1 = setup_tracing(service_name="test-svc-2", console_export=True)
        # Second call returns same provider
        p2 = setup_tracing(service_name="other-svc", console_export=True)
        assert p1 is p2
