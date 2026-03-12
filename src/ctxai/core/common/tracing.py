import time
import uuid
import contextvars
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# Context variable to store the current span ID
current_span_var = contextvars.ContextVar("current_span", default=None)


class Span:
    def __init__(self, name: str, trace_id: str, parent_id: Optional[str] = None):
        self.name = name
        self.trace_id = trace_id
        self.parent_id = parent_id
        self.span_id = str(uuid.uuid4())[:8]
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.attributes: Dict[str, Any] = {}
        self.logs: List[Dict[str, Any]] = []

    def set_attribute(self, key: str, value: Any):
        self.attributes[key] = value

    def add_event(self, name: str, attributes: Dict[str, Any] = None):
        self.logs.append({"timestamp": time.time(), "name": name, "attributes": attributes or {}})

    def finish(self):
        self.end_time = time.time()
        duration = (self.end_time - self.start_time) * 1000
        logger.debug(f"[trace] {self.trace_id}/{self.span_id} {self.name} finished in {duration:.2f}ms")


class Tracer:
    def __init__(self, service_name: str):
        self.service_name = service_name

    def start_span(self, name: str, parent: Optional[Span] = None) -> tuple[Span, contextvars.Token]:
        if parent:
            trace_id = parent.trace_id
            parent_id = parent.span_id
        else:
            # Check context
            current_parent = current_span_var.get()
            if current_parent:
                trace_id = current_parent.trace_id
                parent_id = current_parent.span_id
            else:
                trace_id = str(uuid.uuid4())
                parent_id = None

        span = Span(name, trace_id, parent_id)
        token = current_span_var.set(span)
        return span, token

    def get_current_span(self) -> Optional[Span]:
        return current_span_var.get()

    def _reset_context(self):
        """Internal helper to clear tracing context during tests."""
        current_span_var.set(None)


tracer = Tracer("ctxai")


# Context manager for span
class span_context:
    def __init__(self, name: str, attributes: Dict[str, Any] = None):
        self.name = name
        self.attributes = attributes or {}
        self.span: Optional[Span] = None
        self.token: Optional[contextvars.Token] = None

    def __enter__(self):
        self.span, self.token = tracer.start_span(self.name)
        for k, v in self.attributes.items():
            self.span.set_attribute(k, v)
        return self.span

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.span:
            if exc_type:
                self.span.set_attribute("error", True)
                self.span.set_attribute("exception", str(exc_val))
            self.span.finish()
        if self.token:
            current_span_var.reset(self.token)
