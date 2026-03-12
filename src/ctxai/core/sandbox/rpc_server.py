import os
import subprocess
import asyncio
import resource
import logging
import traceback
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sandbox_rpc")

app = FastAPI(title="Ctx AI Sandbox RPC Server")

class ExecutionRequest(BaseModel):
    command: str
    cwd: Optional[str] = None
    timeout: Optional[float] = 30.0
    user_id: Optional[str] = None
    workspace_id: str = "default"
    policy_name: str = "default"

class ExecutionResponse(BaseModel):
    stdout: str
    stderr: str
    exit_code: int
    duration_s: float

def _get_jailed_path(user_id: Optional[str], workspace_id: str, subpath: Optional[str] = None) -> str:
    # Base workspace directory (e.g. /Users/khulnasoft/Workspaces)
    # In production, this would be a specific volume mount.
    base_dir = os.getenv("A0_WORKSPACES_ROOT", os.path.join(os.getcwd(), "usr", "workspaces"))
    
    tenant_part = f"u_{user_id}" if user_id else "global"
    workspace_path = os.path.join(base_dir, tenant_part, workspace_id)
    
    # Ensure workspace exists
    os.makedirs(workspace_path, exist_ok=True)
    
    if subpath:
        # Prevent path traversal
        abs_subpath = os.path.abspath(os.path.join(workspace_path, subpath))
        if not abs_subpath.startswith(os.path.abspath(workspace_path)):
            raise HTTPException(status_code=403, detail="Path traversal detected")
        return abs_subpath
    
    return workspace_path

@app.get("/health")
async def health():
    return {"status": "ok", "message": "Sandbox RPC server is healthy"}

@app.post("/execute/bash", response_model=ExecutionResponse)
async def execute_bash(request: ExecutionRequest):
    start_time = asyncio.get_event_loop().time()
    try:
        jailed_cwd = _get_jailed_path(request.user_id, request.workspace_id, request.cwd)
        
        # Load policy
        from ctxai.core.sandbox.policies import PolicyRegistry
        policy = PolicyRegistry.get_policy(request.policy_name)
        
        def set_limits():
            if policy.max_memory_mb:
                limit = policy.max_memory_mb * 1024 * 1024
                try:
                    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
                    target_soft = limit
                    target_hard = hard
                    if hard != resource.RLIM_INFINITY and target_soft > hard:
                        target_soft = hard
                    resource.setrlimit(resource.RLIMIT_AS, (target_soft, target_hard))
                except Exception as e:
                    logger.warning(f"Failed to set RLIMIT_AS: {e}")
        
        process = await asyncio.create_subprocess_shell(
            request.command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=jailed_cwd,
            preexec_fn=set_limits
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=request.timeout)
        except asyncio.TimeoutError:
            process.kill()
            stdout, stderr = await process.communicate()
            return ExecutionResponse(
                stdout=stdout.decode(),
                stderr=stderr.decode() + "\n[Execution Timeout]",
                exit_code=-1,
                duration_s=asyncio.get_event_loop().time() - start_time
            )

        return ExecutionResponse(
            stdout=stdout.decode(),
            stderr=stderr.decode(),
            exit_code=process.returncode or 0,
            duration_s=asyncio.get_event_loop().time() - start_time
        )
    except Exception as e:
        logger.error(f"Error in execute_bash: {e}\n{traceback.format_exc()}")
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/execute/python", response_model=ExecutionResponse)
async def execute_python(request: ExecutionRequest):
    import tempfile
    
    jailed_cwd = _get_jailed_path(request.user_id, request.workspace_id, request.cwd)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', dir=jailed_cwd, delete=False) as f:
        f.write(request.command)
        temp_path = f.name

    try:
        start_time = asyncio.get_event_loop().time()
        
        # Load policy
        from ctxai.core.sandbox.policies import PolicyRegistry
        policy = PolicyRegistry.get_policy(request.policy_name)
        
        def set_limits():
            if policy.max_memory_mb:
                limit = policy.max_memory_mb * 1024 * 1024
                try:
                    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
                    target_soft = limit
                    target_hard = hard
                    if hard != resource.RLIM_INFINITY and target_soft > hard:
                        target_soft = hard
                    resource.setrlimit(resource.RLIMIT_AS, (target_soft, target_hard))
                except Exception as e:
                    logger.warning(f"Failed to set RLIMIT_AS: {e}")

        process = await asyncio.create_subprocess_exec(
            "python3", temp_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=jailed_cwd,
            preexec_fn=set_limits
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=request.timeout)
        except asyncio.TimeoutError:
            process.kill()
            stdout, stderr = await process.communicate()
            return ExecutionResponse(
                stdout=stdout.decode(),
                stderr=stderr.decode() + "\n[Execution Timeout]",
                exit_code=-1,
                duration_s=asyncio.get_event_loop().time() - start_time
            )

        return ExecutionResponse(
            stdout=stdout.decode(),
            stderr=stderr.decode(),
            exit_code=process.returncode or 0,
            duration_s=asyncio.get_event_loop().time() - start_time
        )
    except Exception as e:
        logger.error(f"Error in execute_python: {e}\n{traceback.format_exc()}")
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

if __name__ == "__main__":
    import uvicorn
    # Default port for sandbox RPC
    port = int(os.getenv("A0_SANDBOX_PORT", "50002"))
    uvicorn.run(app, host="0.0.0.0", port=port)
