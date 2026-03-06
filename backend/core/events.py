"""
Event system for the Ctx AI framework.

This module provides a simple event system that allows different components
to communicate through events without tight coupling.
"""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class Event:
    """Represents an event in the system."""

    name: str
    data: dict[str, Any]
    timestamp: datetime
    source: str = "unknown"


class EventManager:
    """Manages event subscription and publishing."""

    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, event_name: str, callback: Callable[[Event], None]) -> None:
        """Subscribe to an event."""
        async with self._lock:
            if event_name not in self._subscribers:
                self._subscribers[event_name] = []
            self._subscribers[event_name].append(callback)

    async def unsubscribe(self, event_name: str, callback: Callable[[Event], None]) -> None:
        """Unsubscribe from an event."""
        async with self._lock:
            if event_name in self._subscribers:
                try:
                    self._subscribers[event_name].remove(callback)
                except ValueError:
                    pass  # Callback not found

    async def publish(self, event: Event) -> None:
        """Publish an event to all subscribers."""
        async with self._lock:
            subscribers = self._subscribers.get(event.name, [])

        # Create tasks for all subscribers
        tasks = []
        for callback in subscribers:
            try:
                if asyncio.iscoroutinefunction(callback):
                    tasks.append(callback(event))
                else:
                    # For synchronous callbacks, run them in executor
                    tasks.append(asyncio.get_event_loop().run_in_executor(None, callback, event))
            except Exception as e:
                # Log error but continue with other subscribers
                print(f"Error in event subscriber: {e}")

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def get_subscribed_events(self) -> list[str]:
        """Get list of all subscribed event names."""
        return list(self._subscribers.keys())


# Global event manager instance
_event_manager = EventManager()


def get_event_manager() -> EventManager:
    """Get the global event manager instance."""
    return _event_manager


# Common event names
class EventNames:
    """Constants for common event names."""

    AGENT_CREATED = "agent.created"
    AGENT_STARTED = "agent.started"
    AGENT_STOPPED = "agent.stopped"
    AGENT_ERROR = "agent.error"

    MESSAGE_RECEIVED = "message.received"
    MESSAGE_PROCESSED = "message.processed"
    MESSAGE_ERROR = "message.error"

    TOOL_EXECUTED = "tool.executed"
    TOOL_ERROR = "tool.error"

    CONTEXT_CREATED = "context.created"
    CONTEXT_DELETED = "context.deleted"

    MODEL_CALLED = "model.called"
    MODEL_ERROR = "model.error"
