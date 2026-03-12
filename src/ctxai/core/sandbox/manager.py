import abc
import threading
import os
from typing import Any, Optional, Tuple
from ctxai.core.common.metrics import metrics
from ctxai.core.common.tracing import span_context

# Define metrics
SANDBOX_ENVS_ACTIVE = metrics.gauge("sandbox_envs_active", "Number of active sandbox environments")
SANDBOX_CREATIONS_TOTAL = metrics.counter("sandbox_creations_total", "Total sandbox creations")

class ExecutionContext(abc.ABC):
    """
    Abstract interface for executing code in a sanboxed or controlled environment.
    """
    @abc.abstractmethod
    async def connect(self):
        pass

    @abc.abstractmethod
    async def close(self):
        pass

    @abc.abstractmethod
    async def send_command(self, command: str):
        pass

    @abc.abstractmethod
    async def read_output(self, timeout: float = 0, reset_full_output: bool = False) -> Tuple[str, Optional[str]]:
        pass

class SandboxManager:
    """
    Core Domain: Sandbox & Execution
    Manages the lifecycle of multiple execution environments (Docker, SSH, Local).
    Introduces permission scoping and provider abstraction.
    """
    
    _environments: dict[str, Any] = {}
    _env_lock = threading.RLock()
    
    @staticmethod
    def _get_namespaced_env_id(env_id: str, user_id: Optional[str] = None, workspace_id: Optional[str] = None) -> str:
        parts = []
        if user_id: parts.append(f"u_{user_id}")
        if workspace_id: parts.append(f"w_{workspace_id}")
        parts.append(env_id)
        return ":".join(parts)

    @classmethod
    async def get_environment(cls, env_id: str, provider: Optional[str] = None, user_id: Optional[str] = None, workspace_id: Optional[str] = None, **kwargs) -> Any:
        """
        Factory method to retrieve or create a sandbox environment.
        Namespaces the environment ID by user and workspace if provided.
        """
        full_env_id = cls._get_namespaced_env_id(env_id, user_id, workspace_id)
        
        with cls._env_lock:
            if full_env_id in cls._environments:
                return cls._environments[full_env_id]
        
        # Determine provider: argument > env var > default
        selected_provider = provider or os.getenv("A0_SANDBOX_PROVIDER", "local").lower()
        
        SANDBOX_CREATIONS_TOTAL.inc()
        with span_context("sandbox_create", {"env_id": full_env_id, "provider": selected_provider}):
            # Pass tenant IDs to kwargs for provider-specific jailing (e.g. path jailing)
            kwargs["user_id"] = user_id
            kwargs["workspace_id"] = workspace_id
            
            if selected_provider == "rpc":
                from ctxai.core.sandbox.providers.rpc import RPCExecutionContext
                endpoint = os.getenv("A0_SANDBOX_ENDPOINT", "http://localhost:50002")
                env = RPCExecutionContext(endpoint=endpoint, cwd=kwargs.get("cwd"), user_id=user_id, workspace_id=workspace_id)
            else:
                # Default to local
                from plugins.code_execution.helpers.shell_local import LocalInteractiveSession
                env = LocalInteractiveSession(cwd=kwargs.get("cwd"))
            
            await env.connect()
            
            with cls._env_lock:
                cls._environments[full_env_id] = env
                SANDBOX_ENVS_ACTIVE.set(len(cls._environments))
            return env

    @classmethod
    async def remove_environment(cls, env_id: str, user_id: Optional[str] = None, workspace_id: Optional[str] = None):
        full_env_id = cls._get_namespaced_env_id(env_id, user_id, workspace_id)
        with span_context("sandbox_remove", {"env_id": full_env_id}):
            with cls._env_lock:
                env = cls._environments.pop(full_env_id, None)
                SANDBOX_ENVS_ACTIVE.set(len(cls._environments))
            if env:
                await env.close()

    @classmethod
    async def kill_all(cls):
        with cls._env_lock:
            ids = list(cls._environments.keys())
        for env_id in ids:
            await cls.remove_environment(env_id)
