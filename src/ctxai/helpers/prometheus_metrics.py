"""Prometheus metrics instrumentation for CtxAI.

Exposes a `/metrics` endpoint with standard Prometheus text format.
Instruments:
  - active agent contexts (gauge)
  - task latency histogram (histogram)
  - WebSocket connections (gauge)
  - LLM call counts and latency (counter + histogram)
  - tool execution counts and latency (counter + histogram)
  - memory usage (gauge)
  - message queue depth (gauge)

Usage:
    # At startup
    from ctxai.helpers.prometheus_metrics import metrics, start_metrics_server

    # Record throughout the app
    metrics.observe_task_latency(duration_seconds)
    metrics.set_active_contexts(count)
    metrics.inc_llm_call(provider="openai", model="gpt-4", status="success")
"""

from __future__ import annotations

import functools
import time
from typing import Any

from prometheus_client import Counter, Gauge, Histogram, Info, generate_latest
from prometheus_client.core import CollectorRegistry

# ---------------------------------------------------------------------------
# Registry (isolated to avoid conflicts with other prometheus usage)
# ---------------------------------------------------------------------------
REGISTRY = CollectorRegistry(auto_describe=True)

# ---------------------------------------------------------------------------
# Gauges
# ---------------------------------------------------------------------------
ACTIVE_CONTEXTS = Gauge(
    "ctxai_active_contexts",
    "Number of active agent contexts",
    registry=REGISTRY,
)

WEBSOCKET_CONNECTIONS = Gauge(
    "ctxai_websocket_connections",
    "Number of active WebSocket connections",
    registry=REGISTRY,
)

MESSAGE_QUEUE_DEPTH = Gauge(
    "ctxai_message_queue_depth",
    "Current depth of the internal message queue",
    registry=REGISTRY,
)

MEMORY_RSS_BYTES = Gauge(
    "ctxai_memory_rss_bytes",
    "Resident set size of the process in bytes",
    registry=REGISTRY,
)

MEMORY_VMS_BYTES = Gauge(
    "ctxai_memory_vms_bytes",
    "Virtual memory size of the process in bytes",
    registry=REGISTRY,
)

FAISS_INDEX_SIZE = Gauge(
    "ctxai_faiss_index_size",
    "Number of vectors in the FAISS index",
    registry=REGISTRY,
)

# ---------------------------------------------------------------------------
# Counters
# ---------------------------------------------------------------------------
LLM_CALLS_TOTAL = Counter(
    "ctxai_llm_calls_total",
    "Total number of LLM API calls",
    ["provider", "model", "status"],
    registry=REGISTRY,
)

TOOL_EXECUTIONS_TOTAL = Counter(
    "ctxai_tool_executions_total",
    "Total number of tool executions",
    ["tool_name", "status"],
    registry=REGISTRY,
)

TASKS_TOTAL = Counter(
    "ctxai_tasks_total",
    "Total number of agent tasks",
    ["status"],
    registry=REGISTRY,
)

# ---------------------------------------------------------------------------
# Histograms
# ---------------------------------------------------------------------------
TASK_LATENCY = Histogram(
    "ctxai_task_latency_seconds",
    "End-to-end agent task latency in seconds",
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
    registry=REGISTRY,
)

LLM_CALL_LATENCY = Histogram(
    "ctxai_llm_call_latency_seconds",
    "Latency of individual LLM API calls in seconds",
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
    registry=REGISTRY,
)

TOOL_EXECUTION_LATENCY = Histogram(
    "ctxai_tool_execution_latency_seconds",
    "Latency of tool executions in seconds",
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
    registry=REGISTRY,
)

# ---------------------------------------------------------------------------
# Info
# ---------------------------------------------------------------------------
SERVER_INFO = Info(
    "ctxai_server",
    "CtxAI server metadata",
    registry=REGISTRY,
)


# ---------------------------------------------------------------------------
# Convenience wrapper
# ---------------------------------------------------------------------------
class _Metrics:
    """Thin wrapper around prometheus_client metrics for easy access."""

    # -- Gauges --
    @staticmethod
    def set_active_contexts(count: int) -> None:
        ACTIVE_CONTEXTS.set(count)

    @staticmethod
    def set_websocket_connections(count: int) -> None:
        WEBSOCKET_CONNECTIONS.set(count)

    @staticmethod
    def set_message_queue_depth(depth: int) -> None:
        MESSAGE_QUEUE_DEPTH.set(depth)

    @staticmethod
    def set_memory_usage(rss_bytes: int, vms_bytes: int) -> None:
        MEMORY_RSS_BYTES.set(rss_bytes)
        MEMORY_VMS_BYTES.set(vms_bytes)

    @staticmethod
    def set_faiss_index_size(size: int) -> None:
        FAISS_INDEX_SIZE.set(size)

    # -- Counters --
    @staticmethod
    def inc_llm_call(provider: str, model: str, status: str = "success") -> None:
        LLM_CALLS_TOTAL.labels(provider=provider, model=model, status=status).inc()

    @staticmethod
    def inc_tool_execution(tool_name: str, status: str = "success") -> None:
        TOOL_EXECUTIONS_TOTAL.labels(tool_name=tool_name, status=status).inc()

    @staticmethod
    def inc_task(status: str = "completed") -> None:
        TASKS_TOTAL.labels(status=status).inc()

    # -- Histograms --
    @staticmethod
    def observe_task_latency(duration_seconds: float) -> None:
        TASK_LATENCY.observe(duration_seconds)

    @staticmethod
    def observe_llm_latency(duration_seconds: float) -> None:
        LLM_CALL_LATENCY.observe(duration_seconds)

    @staticmethod
    def observe_tool_latency(duration_seconds: float) -> None:
        TOOL_EXECUTION_LATENCY.observe(duration_seconds)

    # -- Timing helpers --
    @staticmethod
    def timer(histogram: Histogram) -> _Timer:
        """Return a context manager that observes elapsed time on *histogram*.

        Usage:
            with metrics.timer(TASK_LATENCY):
                do_work()
        """
        return _Timer(histogram)

    # -- Export --
    @staticmethod
    def generate_latest() -> bytes:
        return bytes(generate_latest(REGISTRY))

    @staticmethod
    def set_server_info(info: dict[str, str]) -> None:
        SERVER_INFO.info(info)


class _Timer:
    """Context manager / decorator that records elapsed time to a histogram."""

    def __init__(self, histogram: Histogram) -> None:
        self._histogram = histogram
        self._start: float = 0.0

    def __enter__(self) -> _Timer:
        self._start = time.monotonic()
        return self

    def __exit__(self, *_: Any) -> None:
        elapsed = time.monotonic() - self._start
        self._histogram.observe(elapsed)

    def __call__(self, func: Any) -> Any:
        """Use as a decorator."""

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.monotonic()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                self._histogram.observe(time.monotonic() - start)

        return wrapper


# Singleton instance
metrics = _Metrics()
