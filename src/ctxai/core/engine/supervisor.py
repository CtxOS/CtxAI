from typing import Callable, Coroutine, Any
from ctxai.shared.defer import DeferredTask

class AgentSupervisor:
    """
    Core Domain: Agent Supervisor Layer
    Manages the lifecycle, tasks, and recursion of subordinate agents independently 
    of the main string-processing loop in `agent.py`.
    """
    
    @staticmethod
    def run_task(
        context_task: DeferredTask | None,
        context_name: str,
        func: Callable[..., Coroutine[Any, Any, Any]],
        *args: Any,
        **kwargs: Any
    ):
        if not context_task:
            context_task = DeferredTask(
                thread_name=context_name,
            )
        context_task.start_task(func, *args, **kwargs)
        return context_task

    @staticmethod
    def kill_process(context: Any):
        if context and getattr(context, 'task', None):
            context.task.kill()
