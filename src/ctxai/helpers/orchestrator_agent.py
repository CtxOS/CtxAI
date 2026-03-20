"""Orchestrator agent: manages a task queue, worker pool, and routing.

The ``OrchestratorAgent`` wraps a ``TaskQueue`` + ``TaskRouter`` and
dispatches incoming tasks to a pool of worker AgentContexts.  It supports:

- Priority-based task ordering
- Skill-based routing to the best-suited worker
- Per-task timeouts enforced via ``asyncio.wait_for``
- Automatic retry with configurable max attempts and exponential backoff
- Graceful shutdown of the worker pool

Usage::

    orchestrator = OrchestratorAgent(config, max_workers=4)
    orchestrator.register_worker("code_agent", {"code", "debug"}, agent=code_ctx)
    orchestrator.start()
    task_id = orchestrator.submit(Task(description="Fix bug", required_skills=["code"]))
    result = orchestrator.wait_for(task_id, timeout=60)
"""

from __future__ import annotations

import asyncio
import logging
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from ctxai.helpers.defer import DeferredTask
from ctxai.helpers.event_bus import EventBus, EventType
from ctxai.helpers.task_router import AgentSkillProfile, Priority, Task, TaskQueue, TaskRouter

if TYPE_CHECKING:
    from ctxai.agent import Agent, AgentConfig

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Task result tracking
# ---------------------------------------------------------------------------


@dataclass
class TaskResult:
    task_id: str
    status: str  # "completed", "failed", "timeout", "cancelled"
    result: Any = None
    error: str = ""
    attempts: int = 0
    agent_name: str = ""
    started_at: datetime | None = None
    finished_at: datetime | None = None


# ---------------------------------------------------------------------------
# OrchestratorAgent
# ---------------------------------------------------------------------------


class OrchestratorAgent:
    """High-level orchestrator that routes tasks to a pool of workers."""

    def __init__(
        self,
        config: AgentConfig,
        max_workers: int = 4,
        queue_size: int = 256,
        default_timeout: float = 300.0,
        default_retries: int = 2,
        retry_backoff: float = 2.0,
    ) -> None:
        self.config = config
        self.queue = TaskQueue(maxsize=queue_size)
        self.router = TaskRouter()
        self.default_timeout = default_timeout
        self.default_retries = default_retries
        self.retry_backoff = retry_backoff

        self._max_workers = max_workers
        self._results: dict[str, TaskResult] = {}
        self._results_lock = threading.RLock()
        self._running = False
        self._worker_tasks: list[DeferredTask] = []
        self._pending_tasks: dict[str, asyncio.Future] = {}

    # -- worker registration ------------------------------------------------

    def register_worker(
        self,
        agent_name: str,
        skills: set[str] | None = None,
        max_concurrent: int = 1,
        agent: Agent | None = None,
    ) -> None:
        """Register a worker agent with the router."""
        profile = AgentSkillProfile(
            agent_name=agent_name,
            skills=skills or set(),
            max_concurrent=max_concurrent,
        )
        self.router.register(agent_name, profile)
        # Stash the agent reference for dispatch
        if agent:
            self._worker_agents[agent_name] = agent

    _worker_agents: dict[str, Agent] = field(default_factory=dict)  # type: ignore[misc]

    def unregister_worker(self, agent_name: str) -> None:
        self.router.unregister(agent_name)
        self._worker_agents.pop(agent_name, None)

    # -- task submission ----------------------------------------------------

    def submit(self, task: Task) -> str:
        """Submit a task to the queue.  Returns the task id."""
        if not task.timeout:
            task.timeout = self.default_timeout
        if not task.max_retries:
            task.max_retries = self.default_retries
        self.queue.put(task)
        bus = EventBus.get()
        bus.emit(EventType.CUSTOM, custom_name="task_submitted", task_id=task.id, priority=task.priority)
        return task.id

    def submit_immediate(
        self,
        description: str,
        required_skills: list[str] | None = None,
        preferred_agent: str = "",
        timeout: float = 0,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Convenience: create a NORMAL-priority task and submit it."""
        task = Task(
            priority=Priority.NORMAL.value,
            description=description,
            required_skills=required_skills or [],
            preferred_agent=preferred_agent,
            timeout=timeout or self.default_timeout,
            max_retries=self.default_retries,
            metadata=metadata or {},
        )
        return self.submit(task)

    # -- result tracking ----------------------------------------------------

    def get_result(self, task_id: str) -> TaskResult | None:
        with self._results_lock:
            return self._results.get(task_id)

    def wait_for(self, task_id: str, timeout: float | None = None) -> TaskResult | None:
        """Block until the task completes or *timeout* seconds elapse."""
        import time

        deadline = time.monotonic() + (timeout or self.default_timeout)
        while time.monotonic() < deadline:
            result = self.get_result(task_id)
            if result and result.status in ("completed", "failed", "timeout", "cancelled"):
                return result
            time.sleep(0.1)
        return self.get_result(task_id)

    # -- lifecycle ----------------------------------------------------------

    def start(self) -> None:
        """Spin up the worker pool."""
        if self._running:
            return
        self._running = True
        for i in range(self._max_workers):
            worker = DeferredTask(thread_name=f"orch-worker-{i}")
            worker.start_task(self._worker_loop)
            self._worker_tasks.append(worker)

    def stop(self) -> None:
        """Signal workers to drain and stop."""
        self._running = False
        self.queue.close()
        for w in self._worker_tasks:
            w.kill()
        self._worker_tasks.clear()

    # -- worker loop --------------------------------------------------------

    async def _worker_loop(self) -> None:
        """Each worker pulls tasks from the queue and dispatches them."""
        while self._running:
            task = self.queue.get(timeout=1.0)
            if task is None:
                continue
            await self._dispatch_with_retry(task)

    async def _dispatch_with_retry(self, task: Task) -> None:
        """Route a task to an agent, with retry + timeout."""
        last_error = ""
        for attempt in range(1, task.max_retries + 1):
            task.attempts = attempt
            task.status = "running"

            # Route to best agent
            routed = self.router.route_with_load(task)
            if routed is None:
                last_error = "No available agent for task"
                break

            agent_name, profile = routed
            bus = EventBus.get()

            try:
                result = await asyncio.wait_for(
                    self._execute_on_agent(task, agent_name),
                    timeout=task.timeout,
                )
                task.status = "completed"
                task.result = result
                self._record_result(task, agent_name, "completed", result=result)
                bus.emit(
                    EventType.CUSTOM,
                    custom_name="task_completed",
                    task_id=task.id,
                    agent_name=agent_name,
                    attempts=attempt,
                )
                self.router.release_load(agent_name)
                return

            except TimeoutError:
                last_error = f"Timeout after {task.timeout}s (attempt {attempt})"
                task.status = "timeout"
                self.router.release_load(agent_name)
                bus.emit(
                    EventType.CUSTOM,
                    custom_name="task_timeout",
                    task_id=task.id,
                    agent_name=agent_name,
                    attempt=attempt,
                )

            except Exception as e:
                last_error = str(e)
                self.router.release_load(agent_name)
                bus.emit(
                    EventType.CUSTOM,
                    custom_name="task_error",
                    task_id=task.id,
                    agent_name=agent_name,
                    attempt=attempt,
                    error=str(e),
                )

            # Exponential backoff between retries
            if attempt < task.max_retries:
                await asyncio.sleep(self.retry_backoff * attempt)

        # All retries exhausted
        task.status = "failed"
        task.error = last_error
        self._record_result(task, "", "failed", error=last_error)

    async def _execute_on_agent(self, task: Task, agent_name: str) -> Any:
        """Execute a task on a specific agent.

        Subclasses or callers can override this to integrate with
        the full Agent monologue cycle.  The default implementation
        stores the task metadata for the agent to pick up and returns
        a placeholder.
        """
        agent = self._worker_agents.get(agent_name)
        if agent is None:
            # No real agent attached — return metadata as result
            return {"status": "dispatched", "metadata": task.metadata}

        # Store task context on the agent so tools/extensions can read it
        agent.set_data("_current_task", task)
        try:
            # Use the agent's communicate path if there's a message
            msg = task.description or task.metadata.get("message", "")
            if msg:
                from ctxai.agent import UserMessage

                deferred = agent.context.communicate(UserMessage(message=msg))
                result = await deferred.result(timeout=task.timeout)
                return result
            return {"status": "no_action", "task_id": task.id}
        finally:
            agent.data.pop("_current_task", None)

    def _record_result(
        self,
        task: Task,
        agent_name: str,
        status: str,
        result: Any = None,
        error: str = "",
    ) -> None:
        with self._results_lock:
            self._results[task.id] = TaskResult(
                task_id=task.id,
                status=status,
                result=result,
                error=error,
                attempts=task.attempts,
                agent_name=agent_name,
                started_at=task.created_at,
                finished_at=datetime.now(UTC),
            )

    # -- stats --------------------------------------------------------------

    @property
    def pending_count(self) -> int:
        return len(self.queue)

    @property
    def worker_count(self) -> int:
        return len(self._worker_tasks)

    @property
    def registered_agents(self) -> list[str]:
        return self.router.registered_agents
