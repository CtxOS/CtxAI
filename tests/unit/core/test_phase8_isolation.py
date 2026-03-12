import pytest
import os
from unittest.mock import AsyncMock, patch
from ctxai.core.sandbox.manager import SandboxManager
from ctxai.core.engine.persistence import InMemoryProvider

@pytest.mark.asyncio
async def test_sandbox_namespacing_isolation():
    # Setup SandboxManager
    SandboxManager._environments = {}
    
    # Create two environments with same ID but different users
    env_id = "test_env"
    user_a = "user_a"
    user_b = "user_b"
    
    # Mock the session to avoid TTY issues in tests
    with patch("plugins.code_execution.helpers.shell_local.LocalInteractiveSession", side_effect=lambda **kwargs: AsyncMock()) as MockSession:
        
        # Get environment for user A
        env_a = await SandboxManager.get_environment(env_id, provider="local", user_id=user_a)
        # Get environment for user B
        env_b = await SandboxManager.get_environment(env_id, provider="local", user_id=user_b)
        
        # Assert they are different instances (namespaced)
        assert env_a != env_b
        assert len(SandboxManager._environments) == 2
        
        # Verify namespaced IDs
        namespaced_a = SandboxManager._get_namespaced_env_id(env_id, user_a)
        namespaced_b = SandboxManager._get_namespaced_env_id(env_id, user_b)
        
        assert namespaced_a in SandboxManager._environments
        assert namespaced_b in SandboxManager._environments
        assert namespaced_a != namespaced_b
    
    # Clean up
    await SandboxManager.kill_all()

@pytest.mark.asyncio
async def test_persistence_namespacing_isolation():
    provider = InMemoryProvider()
    key = "data"
    user_a = "user_a"
    user_b = "user_b"
    
    provider.set(key, "value_a", user_id=user_a)
    provider.set(key, "value_b", user_id=user_b)
    
    assert provider.get(key, user_id=user_a) == "value_a"
    assert provider.get(key, user_id=user_b) == "value_b"
    
    keys_a = provider.list_keys("*", user_id=user_a)
    keys_b = provider.list_keys("*", user_id=user_b)
    
    assert key in keys_a
    assert key in keys_b
    assert len(keys_a) == 1
    assert len(keys_b) == 1
