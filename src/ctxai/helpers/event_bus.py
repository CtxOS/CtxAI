"""Typed event bus for internal agent-framework events.

Provides a decoupled publish/subscribe mechanism so that orchestration,
reasoning, memory, and UI layers can react to lifecycle events without
reaching into each other's internals.

The bus is intentionally lightweight – it wraps the existing extension
system for backward compatibility while offering a cleaner typed API
for new code.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Any
from typing import Awaitable
from typing import Callable
from typing import Protocol
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Event catalogue
# ---------------------------------------------------------------------------


class EventType(str, Enum):
    """Well-known framework lifecycle events."""

    # Monologue-level
    MONOLOGUE_START = "monologue_start"
    MONOLOGUE_END = "monologue_end"

    # Message-loop iteration
    LOOP_START = "message_loop_start"
    LOOP_END = "message_loop_end"

    # Prompt assembly
    PROMPTS_BEFORE = "message_loop_prompts_before"
    PROMPTS_AFTER = "message_loop_prompts_after"

    # LLM call
    BEFORE_LLM_CALL = "before_main_llm_call"

    # Stream callbacks
    REASONING_CHUNK = "reasoning_stream_chunk"
    REASONING_END = "reasoning_stream_end"
    RESPONSE_CHUNK = "response_stream_chunk"
    RESPONSE_END = "response_stream_end"

    # Tool execution
    TOOL_BEFORE = "tool_execute_before"
    TOOL_AFTER = "tool_execute_after"

    # Process chain
    PROCESS_CHAIN_END = "process_chain_end"

    # Agent lifecycle
    AGENT_INIT = "agent_init"
    CONTEXT_DELETED = "context_deleted"

    # Context timeout
    CONTEXT_TIMEOUT = "context_timeout"

    # Task orchestration
    TASK_SUBMITTED = "task_submitted"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"

    # Custom / extension-defined events
    CUSTOM = "__custom__"


@dataclass(frozen=True)
class Event:
    """Immutable event envelope."""

    type: EventType
    agent: Any  # Agent | None – kept as Any to avoid circular import at runtime
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    data: dict[str, Any] = field(default_factory=dict)
    custom_name: str = ""  # populated when type == CUSTOM


# ---------------------------------------------------------------------------
# Subscriber protocol
# ---------------------------------------------------------------------------


class EventSubscriber(Protocol):
    """Objects that wish to receive events must implement this protocol."""

    def on_event(self, event: Event) -> None | Awaitable[None]: ...


# ---------------------------------------------------------------------------
# Bus implementation
# ---------------------------------------------------------------------------


class EventBus:
    """Singleton event bus.

    Thread-safe for subscribe/unsubscribe.  Event emission is *not*
    serialised – subscribers should be idempotent.
    """

    _instance: EventBus | None = None

    def __init__(self) -> None:
        self._subscribers: dict[EventType, list[EventSubscriber]] = {}
        self._fn_subscribers: dict[EventType, list[Callable[..., Any]]] = {}

    # -- singleton ----------------------------------------------------------

    @classmethod
    def get(cls) -> EventBus:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    # -- subscribe ----------------------------------------------------------

    def subscribe(self, event_type: EventType, subscriber: EventSubscriber) -> None:
        self._subscribers.setdefault(event_type, []).append(subscriber)

    def subscribe_fn(self, event_type: EventType, fn: Callable[..., Any]) -> None:
        """Subscribe a plain callable (simpler than full EventSubscriber)."""
        self._fn_subscribers.setdefault(event_type, []).append(fn)

    def unsubscribe(self, event_type: EventType, subscriber: EventSubscriber) -> None:
        subs = self._subscribers.get(event_type)
        if subs:
            try:
                subs.remove(subscriber)
            except ValueError:
                pass

    # -- publish ------------------------------------------------------------

    def publish(self, event: Event) -> None:
        """Synchronously dispatch an event to all subscribers."""
        # Protocol-based subscribers
        for sub in self._subscribers.get(event.type, []):
            try:
                result = sub.on_event(event)
                if asyncio.iscoroutine(result):
                    # Fire-and-forget – callers that need ordering should use
                    # the async extension system directly.
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(result)  # type: ignore[arg-type]
                    except RuntimeError:
                        asyncio.run(result)  # type: ignore[arg-type]
            except Exception:
                logger.exception("EventBus subscriber error for %s", event.type)

        # Callable-based subscribers
        for fn in self._fn_subscribers.get(event.type, []):
            try:
                result = fn(event)
                if asyncio.iscoroutine(result):
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(result)  # type: ignore[arg-type]
                    except RuntimeError:
                        asyncio.run(result)  # type: ignore[arg-type]
            except Exception:
                logger.exception("EventBus fn-subscriber error for %s", event.type)

    # -- convenience --------------------------------------------------------

    def emit(
        self,
        event_type: EventType,
        agent: Any = None,
        custom_name: str = "",
        **data: Any,
    ) -> None:
        """Shortcut: build an Event and publish it."""
        self.publish(Event(type=event_type, agent=agent, data=data, custom_name=custom_name))
