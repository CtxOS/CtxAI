import asyncio
import pytest
import os
import httpx
from ctxai.core.sandbox.manager import SandboxManager
from ctxai.core.engine.memory import MemoryManager
from ctxai.core.auth.manager import AuthManager

@pytest.mark.asyncio
async def test_memory_isolation():
    """Verify that memory is isolated between different users."""
    user1 = "user1"
    user2 = "user2"
    
    # Register a context for user1
    class DummyContext:
        def __init__(self, id, user_id):
            self.id = id
            self.user_id = user_id
            self.workspace_id = "default"
    
    ctx1 = DummyContext("ctx1", user1)
    MemoryManager.register(ctx1)
    
    # Try to get ctx1 as user1
    retrieved1 = MemoryManager.get("ctx1", user_id=user1)
    assert retrieved1 is not None
    assert retrieved1.id == "ctx1"
    
    # Try to get ctx1 as user2 (should fail)
    retrieved2 = MemoryManager.get("ctx1", user_id=user2)
    assert retrieved2 is None

@pytest.mark.asyncio
async def test_rpc_sandbox_isolation():
    """Verify that execution is jailed and isolated."""
    # Start RPC server in background if not running (simulated or real)
    # For this test, we'll assume the rpc_server.py is running on port 50002
    # In a real CI environment, we'd start it.
    
    # Use a mock or just test the logic of path resolution if RPC server not available
    # Actually, let's test the path jailing logic in rpc_server directly if we can import it
    from ctxai.core.sandbox.rpc_server import _get_jailed_path
    
    user_id = "test_user"
    workspace_id = "test_ws"
    
    # Test base jailing
    jailed_root = _get_jailed_path(user_id, workspace_id)
    assert f"u_{user_id}" in jailed_root
    assert workspace_id in jailed_root
    assert os.path.exists(jailed_root)
    
    # Test path traversal prevention
    with pytest.raises(Exception) as excinfo:
        _get_jailed_path(user_id, workspace_id, "../../../etc/passwd")
    assert "Forbidden" in str(excinfo.value) or "traversal" in str(excinfo.value).lower()

@pytest.mark.asyncio
async def test_sandbox_manager_namespacing():
    """Verify that SandboxManager correctly namespaces environment IDs."""
    env_id = "my_env"
    u1, w1 = "u1", "w1"
    u2, w2 = "u2", "w2"
    
    # We can't easily start full sessions without real shell_local/rpc, 
    # but we can verify the namespacing logic via _get_namespaced_env_id
    sm = SandboxManager()
    
    ns_id1 = sm._get_namespaced_env_id(env_id, u1, w1)
    ns_id2 = sm._get_namespaced_env_id(env_id, u2, w2)
    
    assert ns_id1 != ns_id2
    assert f"u_{u1}" in ns_id1
    assert f"u_{u2}" in ns_id2
