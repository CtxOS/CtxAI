import pytest
import time
from ctxai.core.common.tracing import tracer, span_context

@pytest.fixture(autouse=True)
def reset_trace():
    tracer._reset_context()
    yield
    tracer._reset_context()

def test_span_basic():
    with span_context("test_span", {"attr1": "val1"}) as span:
        assert span.name == "test_span"
        assert span.trace_id is not None
        assert span.parent_id is None
        assert span.attributes["attr1"] == "val1"
        assert span.end_time is None
        
        span.add_event("event1", {"ea": "ev"})
        assert len(span.logs) == 1
        assert span.logs[0]["name"] == "event1"

    assert span.end_time is not None
    assert span.end_time >= span.start_time

def test_span_nesting():
    with span_context("parent") as parent:
        with span_context("child") as child:
            assert child.parent_id == parent.span_id
            assert child.trace_id == parent.trace_id

def test_span_error():
    try:
        with span_context("error_span") as span:
            raise ValueError("test error")
    except ValueError:
        pass
    
    assert span.attributes["error"] is True
    assert "test error" in span.attributes["exception"]

def test_tracer_current_span():
    assert tracer.get_current_span() is None
    with span_context("outer") as outer:
        assert tracer.get_current_span() is outer
        with span_context("inner") as inner:
            assert tracer.get_current_span() is inner
        assert tracer.get_current_span() is outer
    assert tracer.get_current_span() is None
