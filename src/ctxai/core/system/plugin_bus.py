import asyncio
import logging
import inspect
from typing import Any, Callable, Dict, List, Set, Optional
from collections import defaultdict

class PluginBus:
    """
    Lightweight event bus for cross-plugin and system-level communication.
    Supports asynchronous pub/sub patterns.
    """
    _subscribers: Dict[str, Set[Callable]] = defaultdict(set)
    _lock = asyncio.Lock()

    @classmethod
    async def subscribe(cls, event_type: str, callback: Callable[[Any], Any]):
        """Subscribe to an event type."""
        async with cls._lock:
            cls._subscribers[event_type].add(callback)
            logging.debug(f"Subscribed callback to event: {event_type}")

    @classmethod
    async def unsubscribe(cls, event_type: str, callback: Callable[[Any], Any]):
        """Unsubscribe from an event type."""
        async with cls._lock:
            if callback in cls._subscribers[event_type]:
                cls._subscribers[event_type].remove(callback)
                logging.debug(f"Unsubscribed callback from event: {event_type}")

    @classmethod
    async def emit(cls, event_type: str, data: Any = None):
        """
        Emit an event to all subscribers.
        Callbacks are executed asynchronously and errors are caught to prevent bus failure.
        """
        async with cls._lock:
            subscribers = list(cls._subscribers.get(event_type, []))
        
        if not subscribers:
            return

        tasks = []
        for callback in subscribers:
            tasks.append(cls._safe_invoke(callback, data))
        
        await asyncio.gather(*tasks)

    @classmethod
    async def _safe_invoke(cls, callback: Callable, data: Any):
        """Invoke a callback safely, handling both sync and async functions."""
        try:
            if inspect.iscoroutinefunction(callback):
                await callback(data)
            else:
                callback(data)
        except Exception as e:
            logging.error(f"Error in PluginBus callback for {callback}: {e}")
