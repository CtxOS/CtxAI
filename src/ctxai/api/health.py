import os
import time

import psutil

from ctxai.helpers import errors, git
from ctxai.helpers.api import ApiHandler, Request, Response

# Track server start time for uptime calculation
_start_time = time.time()


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

        # Get active contexts count (if available)
        active_contexts = 0
        try:
            # This is a simplified count - in production you'd query the actual manager
            active_contexts = 0  # Placeholder - would need access to websocket_manager
        except Exception:
            pass

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
            "active_contexts": active_contexts,
            "pid": os.getpid(),
        }
