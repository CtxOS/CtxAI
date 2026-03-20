"""Task queue and skill-based routing for agent orchestration.

Provides a priority task queue and a router that dispatches tasks to the
most suitable agent based on declared skill profiles.
"""

from __future__ import annotations

import heapq
import logging
import threading
import uuid
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import IntEnum
from typing import Any
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Priority levels
# ---------------------------------------------------------------------------


class Priority(IntEnum):
    """Task priority — lower value = higher priority."""

    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------


@dataclass(order=True)
class Task:
    """A unit of work to be routed to an agent.

    The ``priority`` field controls heap ordering.  ``created_at``
    provides a secondary tie-breaker (FIFO within the same priority).
    """

    priority: int = field(compare=True)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc), compare=True)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12], compare=False)
    description: str = field(default="", compare=False)
    required_skills: list[str] = field(default_factory=list, compare=False)
    preferred_agent: str = field(default="", compare=False)
    timeout: float = field(default=0.0, compare=False)
    max_retries: int = field(default=0, compare=False)
    metadata: dict[str, Any] = field(default_factory=dict, compare=False)
    status: str = field(default="pending", compare=False)
    result: Any = field(default=None, compare=False)
    error: str = field(default="", compare=False)
    attempts: int = field(default=0, compare=False)


# ---------------------------------------------------------------------------
# Agent skill profile
# ---------------------------------------------------------------------------


@dataclass
class AgentSkillProfile:
    """Describes the capabilities of a single agent.

    ``skills`` is a set of capability labels (e.g. ``{"code", "browser"}``).
    ``max_concurrent`` limits how many tasks this agent can handle at once.
    """

    agent_name: str
    skills: set[str] = field(default_factory=set)
    max_concurrent: int = 3
    current_load: int = 0

    def can_accept(self) -> bool:
        return self.current_load < self.max_concurrent

    def score_for(self, required_skills: list[str]) -> float:
        """Return a fitness score (0..1) for the given skill requirements."""
        if not required_skills:
            return 0.5  # neutral score for general tasks
        matched = sum(1 for s in required_skills if s in self.skills)
        return matched / len(required_skills)


# ---------------------------------------------------------------------------
# Task queue
# ---------------------------------------------------------------------------


class TaskQueue:
    """Thread-safe priority queue for tasks.

    Enqueue with ``put``, dequeue with ``get`` (blocking with optional
    timeout).  Capacity is bounded; ``put`` raises ``RuntimeError`` when
    the queue is full unless ``block=False``.
    """

    def __init__(self, maxsize: int = 256) -> None:
        self._maxsize = maxsize
        self._heap: list[Task] = []
        self._lock = threading.RLock()
        self._not_empty = threading.Condition(self._lock)
        self._closed = False

    def put(self, task: Task, block: bool = True) -> None:
        with self._not_empty:
            if len(self._heap) >= self._maxsize:
                if not block:
                    raise RuntimeError("TaskQueue is full")
                # Wait for space
                while len(self._heap) >= self._maxsize and not self._closed:
                    self._not_empty.wait(timeout=1.0)
            if self._closed:
                raise RuntimeError("TaskQueue is closed")
            heapq.heappush(self._heap, task)
            self._not_empty.notify()

    def get(self, timeout: float | None = None) -> Task | None:
        """Dequeue the highest-priority task.  Returns ``None`` on timeout or close."""
        with self._not_empty:
            while not self._heap and not self._closed:
                if not self._not_empty.wait(timeout=timeout):
                    return None
            if self._closed and not self._heap:
                return None
            return heapq.heappop(self._heap)

    def peek(self) -> Task | None:
        with self._lock:
            return self._heap[0] if self._heap else None

    def close(self) -> None:
        with self._not_empty:
            self._closed = True
            self._not_empty.notify_all()

    def __len__(self) -> int:
        with self._lock:
            return len(self._heap)

    @property
    def empty(self) -> bool:
        return len(self) == 0

    @property
    def full(self) -> bool:
        return len(self) >= self._maxsize


# ---------------------------------------------------------------------------
# Task router
# ---------------------------------------------------------------------------


class TaskRouter:
    """Routes tasks to the best-suited agent based on skill profiles.

    Usage::

        router = TaskRouter()
        router.register("code_agent", AgentSkillProfile("code_agent", {"code", "debug"}))
        router.register("browser_agent", AgentSkillProfile("browser_agent", {"browser", "web"}))

        agent_name = router.route(task)
    """

    def __init__(self) -> None:
        self._profiles: dict[str, AgentSkillProfile] = {}
        self._lock = threading.Lock()

    def register(self, agent_name: str, profile: AgentSkillProfile) -> None:
        with self._lock:
            self._profiles[agent_name] = profile

    def unregister(self, agent_name: str) -> None:
        with self._lock:
            self._profiles.pop(agent_name, None)

    def get_profile(self, agent_name: str) -> AgentSkillProfile | None:
        with self._lock:
            return self._profiles.get(agent_name)

    def route(self, task: Task) -> str | None:
        """Return the name of the best agent for *task*, or ``None`` if no agent fits."""
        with self._lock:
            # Preferred agent takes priority if available
            if task.preferred_agent:
                pref = self._profiles.get(task.preferred_agent)
                if pref and pref.can_accept():
                    return task.preferred_agent

            # Score all available agents
            candidates: list[tuple[float, str]] = []
            for name, profile in self._profiles.items():
                if not profile.can_accept():
                    continue
                score = profile.score_for(task.required_skills)
                if score > 0:
                    candidates.append((score, name))

            if not candidates:
                # Fall back to any agent that can accept (general routing)
                for name, profile in self._profiles.items():
                    if profile.can_accept():
                        candidates.append((0.1, name))

            if not candidates:
                return None

            # Highest score first
            candidates.sort(key=lambda x: x[0], reverse=True)
            return candidates[0][1]

    def route_with_load(self, task: Task) -> tuple[str, AgentSkillProfile] | None:
        """Route and return (agent_name, profile), incrementing the profile load."""
        with self._lock:
            name = self.route(task)
            if name is None:
                return None
            profile = self._profiles[name]
            profile.current_load += 1
            return name, profile

    def release_load(self, agent_name: str) -> None:
        with self._lock:
            profile = self._profiles.get(agent_name)
            if profile and profile.current_load > 0:
                profile.current_load -= 1

    @property
    def registered_agents(self) -> list[str]:
        with self._lock:
            return list(self._profiles.keys())
