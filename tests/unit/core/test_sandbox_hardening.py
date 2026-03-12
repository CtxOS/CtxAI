import asyncio
import pytest
import httpx
import time
import os
from ctxai.core.sandbox.rpc_server import app
from ctxai.core.sandbox.policies import STRICT_POLICY

@pytest.mark.asyncio
async def test_sandbox_resource_limits():
    """Verify that the strict policy correctly limits memory and execution."""
    # We'll use a local instance of the FastAPI app for testing if possible,
    # but the rpc_server typically runs as a separate process.
    # For this test, let's assume the RPC server is reachable at localhost:50002
    
    # We need to start the RPC server or mock the response.
    # Since the user has one running in terminal, we can try to talk to it.
    
    url = "http://localhost:50002/execute/python"
    
    # Try a memory-intensive task with strict policy (256MB)
    # Let's try to allocate 500MB.
    
    command = "import array; a = array.array('B', [0] * 500 * 1024 * 1024)"
    
    async with httpx.AsyncClient() as client:
        try:
            # Increase timeout to 10s to be safe
            resp = await client.post(url, json={
                "command": command,
                "policy_name": "strict",
                "timeout": 10.0
            }, timeout=15.0)
            
            data = resp.json()
            # If it failed due to memory, it should have a non-zero exit code or error in stderr
            assert resp.status_code == 200
            # On hit limit, it should fail.
            assert data["exit_code"] != 0 or "MemoryError" in data["stderr"] or "[Memory Error]" in data["stderr"]
        except httpx.ConnectError:
            pytest.skip("RPC server not running on localhost:50002")

@pytest.mark.asyncio
async def test_sandbox_timeout():
    """Verify that time limits are enforced."""
    url = "http://localhost:50002/execute/bash"
    
    async with httpx.AsyncClient() as client:
        try:
            # Command that sleeps longer than default strict timeout (15s) or request timeout
            resp = await client.post(url, json={
                "command": "sleep 10",
                "timeout": 2.0 # Request overrides policy? No, rpc_server uses request.timeout
            })
            
            data = resp.json()
            assert data["exit_code"] == -1
            assert "[Execution Timeout]" in data["stderr"]
        except httpx.ConnectError:
            pytest.skip("RPC server not running on localhost:50002")
