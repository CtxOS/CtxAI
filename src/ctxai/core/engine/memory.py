import threading
import os
from datetime import datetime, timezone
from typing import Any, Optional
import random
import string

from ctxai.shared import context as context_helper
import ctxai.shared.log as Log
from ctxai.shared.defer import DeferredTask
from ctxai import models
from ctxai.core.engine.persistence import PersistenceProvider, InMemoryProvider

class MemoryManager:
    """
    Core Domain: Memory Management
    Responsible for handling Context Lifecycles, Session Histories, and Semantic Deduplication.
    Extracted from the monolithic agent.py AgentContext class.
    """
    
    
    _provider: PersistenceProvider = InMemoryProvider()
    _contexts_lock = threading.RLock()
    _counter: int = 0
    _notification_manager = None

    @classmethod
    def set_provider(cls, provider: PersistenceProvider):
        with cls._contexts_lock:
            cls._provider = provider
    
    @classmethod
    def get_provider(cls) -> PersistenceProvider:
        return cls._provider
    
    @classmethod
    def _get_tenant_ids(cls, user_id: Optional[str] = None, workspace_id: Optional[str] = None) -> tuple[Optional[str], Optional[str]]:
        """Helper to resolve user/workspace IDs from arguments or context."""
        uid = user_id or context_helper.get_context_data("user_id")
        wid = workspace_id or context_helper.get_context_data("workspace_id", "default")
        return uid, wid

    @classmethod
    def generate_id(cls) -> str:
        def generate_short_id():
            return "".join(random.choices(string.ascii_letters + string.digits, k=8))

        uid, wid = cls._get_tenant_ids()
        while True:
            short_id = generate_short_id()
            if not cls._provider.exists(short_id, user_id=uid, workspace_id=wid):
                return short_id

    @classmethod
    def get(cls, id: str, user_id: Optional[str] = None, workspace_id: Optional[str] = None):
        uid, wid = cls._get_tenant_ids(user_id, workspace_id)
        return cls._provider.get(id, user_id=uid, workspace_id=wid)

    @classmethod
    def get_namespaced(cls, id: str, user_id: str, workspace_id: str = "default"):
        """Explicitly get context from a specific user/workspace namespace."""
        return cls._provider.get(id, user_id=user_id, workspace_id=workspace_id)

    @classmethod
    def current(cls):
        ctxid = context_helper.get_context_data("agent_context_id", "")
        if not ctxid:
            return None
        return cls.get(ctxid)

    @classmethod
    def set_current(cls, ctxid: str):
        context_helper.set_context_data("agent_context_id", ctxid)

    @classmethod
    def first(cls, user_id: Optional[str] = None, workspace_id: Optional[str] = None):
        uid, wid = cls._get_tenant_ids(user_id, workspace_id)
        keys = cls._provider.list_keys(user_id=uid, workspace_id=wid)
        if not keys:
            return None
        return cls.get(keys[0], user_id=uid, workspace_id=wid)

    @classmethod
    def all(cls, user_id: Optional[str] = None, workspace_id: Optional[str] = None):
        uid, wid = cls._get_tenant_ids(user_id, workspace_id)
        keys = cls._provider.list_keys(user_id=uid, workspace_id=wid)
        return [cls.get(k, user_id=uid, workspace_id=wid) for k in keys if cls.get(k, user_id=uid, workspace_id=wid)]

    @classmethod
    def register(cls, context: Any, set_current: bool = False):
        user_id = getattr(context, 'user_id', None)
        workspace_id = getattr(context, 'workspace_id', 'default')
        uid, wid = cls._get_tenant_ids(user_id, workspace_id)
        
        with cls._contexts_lock:
            existing = cls._provider.get(context.id, user_id=uid, workspace_id=wid)
            if existing:
                cls._provider.delete(context.id, user_id=uid, workspace_id=wid)
                if getattr(existing, 'task', None):
                    existing.task.kill()
            cls._provider.set(context.id, context, user_id=uid, workspace_id=wid)
            if set_current:
                cls.set_current(context.id)
        cls._counter += 1
        return cls._counter

    @classmethod
    def remove(cls, id: str, user_id: Optional[str] = None, workspace_id: Optional[str] = None):
        uid, wid = cls._get_tenant_ids(user_id, workspace_id)
        with cls._contexts_lock:
            context = cls._provider.get(id, user_id=uid, workspace_id=wid)
            cls._provider.delete(id, user_id=uid, workspace_id=wid)
        if context and getattr(context, 'task', None):
            context.task.kill()
        
        # Cleanup sandbox environments associated with this context
        try:
            import asyncio
            from ctxai.core.sandbox.manager import SandboxManager
            # We don't know all session IDs here, but we can try common ones or just let SandboxManager handle patterns
            # In a real future state, we would track session IDs in the context data.
            # For now, we fire a background task to cleanup environmental resources.
            async def cleanup_env():
                for s in range(5): # try first 5 sessions
                    await SandboxManager.remove_environment(f"{id}_{s}")
            
            # Since remove is sync (legacy), we run the cleanup in the event loop if it exists
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(cleanup_env())
            except RuntimeError:
                pass
        except ImportError:
            pass
            
        return context
