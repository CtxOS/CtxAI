import httpx
import os
from typing import Tuple, Optional
from ctxai.core.sandbox.manager import ExecutionContext
from ctxai.core.common.tracing import span_context

class RPCExecutionContext(ExecutionContext):
    """
    ExecutionContext implementation that proxies execution to a remote RPC server.
    """
    def __init__(self, endpoint: str, timeout: float = 30.0, cwd: Optional[str] = None, user_id: Optional[str] = None, workspace_id: str = "default", policy_name: str = "default"):
        self.endpoint = endpoint
        self.timeout = timeout
        self.cwd = cwd
        self.user_id = user_id
        self.workspace_id = workspace_id
        self.policy_name = policy_name
        self.client = httpx.AsyncClient(base_url=self.endpoint, timeout=timeout)
        self._last_stdout = ""
        self._last_stderr = ""
        self._last_exit_code = 0

    async def connect(self):
        # Verify connectivity
        try:
            response = await self.client.get("/health")
            response.raise_for_status()
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Sandbox RPC at {self.endpoint}: {e}")

    async def close(self):
        await self.client.aclose()

    async def send_command(self, command: str):
        """
        Executes a bash command via RPC.
        Note: This implementation follows the 'send_command' then 'read_output' pattern
        required by the Ctx AI tool system, but simulates it over stateless HTTP.
        """
        with span_context("rpc_execute_bash"):
            payload = {
                "command": command,
                "cwd": self.cwd,
                "timeout": self.timeout,
                "user_id": self.user_id,
                "workspace_id": self.workspace_id,
                "policy_name": self.policy_name
            }
            response = await self.client.post("/execute/bash", json=payload)
            response.raise_for_status()
            result = response.json()
            
            self._last_stdout = result["stdout"]
            self._last_stderr = result["stderr"]
            self._last_exit_code = result["exit_code"]

    async def read_output(self, timeout: float = 0, reset_full_output: bool = False) -> Tuple[str, Optional[str]]:
        """
        Returns the output from the last executed command.
        """
        stdout = self._last_stdout
        stderr = self._last_stderr if self._last_stderr else None
        
        if reset_full_output:
            self._last_stdout = ""
            self._last_stderr = ""
            
        return stdout, stderr

    async def execute_python(self, code: str) -> Tuple[str, str, int]:
        """
        Dedicated method for Python execution via RPC.
        """
        with span_context("rpc_execute_python"):
            payload = {
                "command": code,
                "cwd": self.cwd,
                "timeout": self.timeout,
                "user_id": self.user_id,
                "workspace_id": self.workspace_id,
                "policy_name": self.policy_name
            }
            response = await self.client.post("/execute/python", json=payload)
            response.raise_for_status()
            result = response.json()
            return result["stdout"], result["stderr"], result["exit_code"]
