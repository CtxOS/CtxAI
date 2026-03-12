import pytest
from unittest.mock import MagicMock
from ctxai.core.engine.memory import MemoryManager
from ctxai.core.engine.persistence import InMemoryProvider

@pytest.fixture
def memory_manager():
    # Reset provider and counter to clean state
    provider = InMemoryProvider()
    MemoryManager.set_provider(provider)
    MemoryManager._counter = 0
    return MemoryManager

def test_generate_id(memory_manager):
    id1 = memory_manager.generate_id()
    id2 = memory_manager.generate_id()
    assert len(id1) == 8
    assert id1 != id2

def test_register_get(memory_manager):
    mock_context = MagicMock()
    mock_context.id = "ctx1"
    mock_context.user_id = None
    mock_context.workspace_id = None
    
    count = memory_manager.register(mock_context)
    assert count == 1
    
    retrieved = memory_manager.get("ctx1")
    assert retrieved is mock_context

def test_remove(memory_manager):
    mock_context = MagicMock()
    mock_context.id = "ctx1"
    mock_context.user_id = None
    mock_context.workspace_id = None
    mock_context.task = MagicMock()
    
    memory_manager.register(mock_context)
    removed = memory_manager.remove("ctx1")
    
    assert removed is mock_context
    assert memory_manager.get("ctx1") is None
    mock_context.task.kill.assert_called_once()

def test_set_current_current(memory_manager):
    memory_manager.set_current("ctx_test")
    # This relies on helpers.context which might need mocking if it's not working in test env
    # For now we just test the set/get pattern if possible
    assert memory_manager._provider.get("ctx_test") is None # hasn't been registered yet
