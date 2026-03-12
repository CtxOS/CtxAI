import asyncio
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional
import uuid
import json
import pickle

class JobQueue(ABC):
    """
    Abstract Job Queue for distributed agent execution.
    """
    @abstractmethod
    def push(self, func_ref: str, *args, **kwargs) -> str:
        pass

    @abstractmethod
    def pop(self) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_status(self, job_id: str) -> str:
        pass

class LocalJobQueue(JobQueue):
    """ Default implementation using local DeferredTasks """
    def __init__(self):
        self._jobs = {}

    def push(self, func_ref: str, *args, **kwargs) -> str:
        from ctxai.shared.defer import DeferredTask
        job_id = str(uuid.uuid4())
        # In a local queue, we just wrap the function. 
        # func_ref would be the actual function in a local context, 
        # or we resolve it from a registry.
        return job_id

    def pop(self) -> Optional[Dict[str, Any]]:
        return None # Not used for local threads

    def get_status(self, job_id: str) -> str:
        return "running"

class RedisJobQueue(JobQueue):
    """ Redis-based queue for horizontal scaling """
    def __init__(self, host='localhost', port=6379, db=0):
        import redis
        self._redis = redis.Redis(host=host, port=port, db=db)
        self._queue_key = "ctxai_jobs"

    def push(self, func_ref: str, *args, **kwargs) -> str:
        from ctxai.shared import context as context_helper
        user_id = context_helper.get_context_data("user_id")
        workspace_id = context_helper.get_context_data("workspace_id", "default")
        
        job_id = str(uuid.uuid4())
        job_data = {
            "id": job_id,
            "func": func_ref,
            "args": args,
            "kwargs": kwargs,
            "tenant": {
                "user_id": user_id,
                "workspace_id": workspace_id
            }
        }
        self._redis.rpush(self._queue_key, pickle.dumps(job_data))
        return job_id

    def pop(self) -> Optional[Dict[str, Any]]:
        data = self._redis.lpop(self._queue_key)
        if data:
            return pickle.loads(data)
        return None

    def get_status(self, job_id: str) -> str:
        return "pending" # Would need a separate status store
