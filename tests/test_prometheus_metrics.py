"""Unit tests for Prometheus metrics instrumentation."""

import time

from ctxai.helpers.prometheus_metrics import (
    REGISTRY,
    TASK_LATENCY,
    TOOL_EXECUTION_LATENCY,
    metrics,
)

# ---------------------------------------------------------------------------
# Gauge tests
# ---------------------------------------------------------------------------


class TestGauges:
    def test_set_active_contexts(self):
        metrics.set_active_contexts(42)
        # Verify via collect
        for metric in REGISTRY.collect():
            if metric.name == "ctxai_active_contexts":
                for sample in metric.samples:
                    if sample.name == "ctxai_active_contexts":
                        assert sample.value == 42

    def test_set_websocket_connections(self):
        metrics.set_websocket_connections(10)
        for metric in REGISTRY.collect():
            if metric.name == "ctxai_websocket_connections":
                for sample in metric.samples:
                    if sample.name == "ctxai_websocket_connections":
                        assert sample.value == 10


# ---------------------------------------------------------------------------
# Counter tests
# ---------------------------------------------------------------------------


class TestCounters:
    def test_inc_llm_call(self):
        metrics.inc_llm_call(provider="openai", model="gpt-4", status="success")
        # Just verify no exception

    def test_inc_tool_execution(self):
        metrics.inc_tool_execution(tool_name="bash", status="success")

    def test_inc_task(self):
        metrics.inc_task(status="completed")


# ---------------------------------------------------------------------------
# Histogram tests
# ---------------------------------------------------------------------------


class TestHistograms:
    def test_observe_task_latency(self):
        metrics.observe_task_latency(1.5)

    def test_observe_llm_latency(self):
        metrics.observe_llm_latency(0.8)

    def test_observe_tool_latency(self):
        metrics.observe_tool_latency(0.2)


# ---------------------------------------------------------------------------
# Timer tests
# ---------------------------------------------------------------------------


class TestTimer:
    def test_timer_as_context_manager(self):
        with metrics.timer(TASK_LATENCY):
            time.sleep(0.05)

    def test_timer_as_decorator(self):
        @metrics.timer(TOOL_EXECUTION_LATENCY)
        def slow_function():
            time.sleep(0.05)
            return "done"

        result = slow_function()
        assert result == "done"


# ---------------------------------------------------------------------------
# generate_latest
# ---------------------------------------------------------------------------


class TestGenerateLatest:
    def test_returns_bytes(self):
        data = metrics.generate_latest()
        assert isinstance(data, bytes)
        assert b"ctxai_active_contexts" in data

    def test_output_is_prometheus_format(self):
        data = metrics.generate_latest().decode()
        # Prometheus format starts with # HELP or # TYPE
        assert "# HELP" in data or "# TYPE" in data
