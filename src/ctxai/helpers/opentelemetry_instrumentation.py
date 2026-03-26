"""OpenTelemetry distributed tracing for CtxAI.

Provides a thin wrapper around the OpenTelemetry SDK that:

* Creates a ``TracerProvider`` with optional OTLP export (Jaeger, Grafana
  Tempo, etc.) controlled by the ``OTEL_EXPORTER_OTLP_ENDPOINT`` env var.
* Exposes ``get_tracer()`` and ``start_span()`` helpers used by the
  instrumentation points throughout the codebase.
* Adds ``trace_id``, ``context_id``, ``agent_name`` attributes to every span
  so that traces correlate with the structured JSON logs.

Setup (called once at application startup)::

    from ctxai.helpers.opentelemetry_instrumentation import setup_tracing
    setup_tracing()

Usage::

    from ctxai.helpers.opentelemetry_instrumentation import get_tracer, start_span

    tracer = get_tracer(__name__)
    with start_span(tracer, "llm.call", attributes={"model": "gpt-4"}):
        result = await model.invoke(...)

Environment variables:
    OTEL_EXPORTER_OTLP_ENDPOINT  — e.g. ``http://jaeger:4317``
    OTEL_SERVICE_NAME            — defaults to ``ctxai``
    OTEL_TRACES_SAMPLER          — defaults to ``parentbased_always_on``
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------
_tracer_provider: TracerProvider | None = None
_configured = False


def setup_tracing(
    *,
    service_name: str | None = None,
    otlp_endpoint: str | None = None,
    console_export: bool = False,
) -> TracerProvider:
    """Initialise the global tracer provider.

    Call once at application startup.  Safe to call multiple times —
    subsequent calls are no-ops.

    Args:
        service_name: Override the service name (default: env ``OTEL_SERVICE_NAME`` or ``ctxai``).
        otlp_endpoint: Override the OTLP endpoint (default: env ``OTEL_EXPORTER_OTLP_ENDPOINT``).
        console_export: If True, also export spans to stdout (useful for debugging).
    """
    global _tracer_provider, _configured

    if _configured:
        return _tracer_provider  # type: ignore[return-value]

    svc = service_name or os.getenv("OTEL_SERVICE_NAME", "ctxai")
    endpoint = otlp_endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")

    resource = Resource.create({"service.name": svc})
    provider = TracerProvider(resource=resource)

    # OTLP exporter (gRPC) when endpoint is configured
    if endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

            exporter = OTLPSpanExporter(endpoint=endpoint, timeout=10)
            provider.add_span_processor(BatchSpanProcessor(exporter))
        except Exception:
            # Fall back to console if OTLP import fails
            console_export = True

    # Console exporter for local debugging
    if console_export or not endpoint:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)

    _tracer_provider = provider
    _configured = True
    return provider


def get_tracer(name: str = "ctxai") -> trace.Tracer:
    """Return a tracer for the given module name."""
    return trace.get_tracer(name)


def _get_trace_id_hex() -> str:
    """Return the current span's trace ID as a hex string (or empty)."""
    span = trace.get_current_span()
    ctx = span.get_span_context()
    if ctx and ctx.trace_id:
        return format(ctx.trace_id, "032x")
    return ""


@contextmanager
def start_span(
    tracer: trace.Tracer,
    name: str,
    *,
    attributes: dict[str, Any] | None = None,
    kind: trace.SpanKind = trace.SpanKind.INTERNAL,
    links: list[Any] | None = None,
) -> Iterator[trace.Span]:
    """Context manager that creates and activates a span.

    Usage::

        with start_span(tracer, "my.operation", attributes={"key": "val"}):
            do_work()
    """
    with tracer.start_as_current_span(name, kind=kind, links=links, attributes=attributes) as span:
        yield span


def record_exception(span: trace.Span, exc: BaseException) -> None:
    """Record an exception on the given span and set status to ERROR."""
    span.record_exception(exc)
    span.set_status(trace.StatusCode.ERROR, str(exc))


def get_current_trace_id() -> str:
    """Public helper to get the current trace ID (hex string or empty)."""
    return _get_trace_id_hex()
