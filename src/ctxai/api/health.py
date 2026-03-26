import os
import time

import psutil

from ctxai.helpers import errors, git
from ctxai.helpers.api import ApiHandler, Request, Response
from ctxai.helpers.prometheus_metrics import metrics

# Track server start time for uptime calculation
_start_time = time.time()


def _get_context_stats() -> dict:
    """Return context pool stats from AgentContext."""
    try:
        from ctxai.agent import AgentContext

        contexts = AgentContext.all()
        running = sum(1 for c in contexts if c.is_running())
        return {
            "total": len(contexts),
            "running": running,
            "max": AgentContext.get_max_contexts(),
            "max_concurrent_tasks": AgentContext.get_max_concurrent_tasks(),
        }
    except Exception:
        return {"total": 0, "running": 0, "max": 0, "max_concurrent_tasks": 0}


def _get_provider_info() -> dict:
    """Return summary of configured LLM provider types."""
    try:
        from ctxai.helpers.providers import get_providers

        chat_providers = get_providers("chat")
        embedding_providers = get_providers("embedding")
        return {
            "chat_count": len(chat_providers),
            "embedding_count": len(embedding_providers),
        }
    except Exception:
        return {"chat_count": 0, "embedding_count": 0}


class HealthCheck(ApiHandler):
    @classmethod
    def requires_auth(cls) -> bool:
        return False

    @classmethod
    def requires_csrf(cls) -> bool:
        return False

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET", "POST"]

    async def process(self, input: dict, request: Request) -> dict | Response:
        gitinfo = None
        error = None
        try:
            gitinfo = git.get_git_info()
        except Exception as e:
            error = errors.error_text(e)

        # Gather system metrics
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()

        # Push memory usage to Prometheus gauges
        metrics.set_memory_usage(memory_info.rss, memory_info.vms)

        # Context pool stats
        contexts = _get_context_stats()

        # Compute aggregate message queue depth across all contexts
        try:
            from ctxai.agent import AgentContext
            from ctxai.helpers.message_queue import get_queue

            total_queue_depth = sum(len(get_queue(c)) for c in AgentContext.all())
        except Exception:
            total_queue_depth = 0
        metrics.set_message_queue_depth(total_queue_depth)

        # LLM provider summary
        providers = _get_provider_info()

        return {
            "status": "ok",
            "uptime_seconds": round(time.time() - _start_time, 2),
            "gitinfo": gitinfo,
            "error": error,
            "memory": {
                "rss_mb": round(memory_info.rss / 1024 / 1024, 2),
                "vms_mb": round(memory_info.vms / 1024 / 1024, 2),
            },
            "cpu_percent": process.cpu_percent(interval=0.1),
            "contexts": contexts,
            "providers": providers,
            "message_queue_depth": total_queue_depth,
            "pid": os.getpid(),
        }
