import os
import json
import pickle
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

class PersistenceProvider(ABC):
    """
    Abstract Base Class for Persistence Providers.
    Allows switching between In-Memory, Redis, and Database storage.
    """
    
    @abstractmethod
    def get(self, key: str, user_id: Optional[str] = None, workspace_id: Optional[str] = None) -> Optional[Any]:
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None, user_id: Optional[str] = None, workspace_id: Optional[str] = None):
        pass

    @abstractmethod
    def delete(self, key: str, user_id: Optional[str] = None, workspace_id: Optional[str] = None):
        pass

    def _get_namespaced_key(self, key: str, user_id: Optional[str] = None, workspace_id: Optional[str] = None) -> str:
        parts = []
        if user_id: parts.append(f"user:{user_id}")
        if workspace_id: parts.append(f"ws:{workspace_id}")
        parts.append(key)
        return ":".join(parts)

class InMemoryProvider(PersistenceProvider):
    """ Default implementation using a local dictionary """
    def __init__(self):
        self._storage: Dict[str, Any] = {}

    def get(self, key: str, user_id: Optional[str] = None, workspace_id: Optional[str] = None) -> Optional[Any]:
        full_key = self._get_namespaced_key(key, user_id, workspace_id)
        return self._storage.get(full_key)

    def set(self, key: str, value: Any, ttl: Optional[int] = None, user_id: Optional[str] = None, workspace_id: Optional[str] = None):
        full_key = self._get_namespaced_key(key, user_id, workspace_id)
        self._storage[full_key] = value

    def delete(self, key: str, user_id: Optional[str] = None, workspace_id: Optional[str] = None):
        full_key = self._get_namespaced_key(key, user_id, workspace_id)
        self._storage.pop(full_key, None)

    def list_keys(self, pattern: str = "*", user_id: Optional[str] = None, workspace_id: Optional[str] = None) -> List[str]:
        prefix = self._get_namespaced_key("", user_id, workspace_id)
        search_pattern = f"{prefix}{pattern}"
        import fnmatch
        keys = [k for k in self._storage.keys() if fnmatch.fnmatch(k, search_pattern)]
        return [k[len(prefix):] for k in keys]

    def exists(self, key: str, user_id: Optional[str] = None, workspace_id: Optional[str] = None) -> bool:
        full_key = self._get_namespaced_key(key, user_id, workspace_id)
        return full_key in self._storage

class RedisProvider(PersistenceProvider):
    """ Redis implementation for distributed state """
    def __init__(self, host='localhost', port=6379, db=0, password=None):
        import redis
        self._redis = redis.Redis(host=host, port=port, db=db, password=password)

    def get(self, key: str, user_id: Optional[str] = None, workspace_id: Optional[str] = None) -> Optional[Any]:
        full_key = self._get_namespaced_key(key, user_id, workspace_id)
        data = self._redis.get(full_key)
        if data:
            try:
                # Try to deserialize context objects
                return pickle.loads(data)
            except Exception:
                return data.decode('utf-8')
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None, user_id: Optional[str] = None, workspace_id: Optional[str] = None):
        full_key = self._get_namespaced_key(key, user_id, workspace_id)
        if isinstance(value, (dict, list, str, int, float, bool)) or value is None:
            data = json.dumps(value)
        else:
            # For complex objects like AgentContext
            data = pickle.dumps(value)
        
        self._redis.set(full_key, data, ex=ttl)

    def delete(self, key: str, user_id: Optional[str] = None, workspace_id: Optional[str] = None):
        full_key = self._get_namespaced_key(key, user_id, workspace_id)
        self._redis.delete(full_key)

    def list_keys(self, pattern: str = "*", user_id: Optional[str] = None, workspace_id: Optional[str] = None) -> List[str]:
        # Note: pattern is applied AFTER namespacing logic if we were to be fully consistent,
        # but for simple pattern matching we just use redis native keys.
        prefix = self._get_namespaced_key("", user_id, workspace_id)
        search_pattern = f"{prefix}{pattern}"
        keys = self._redis.keys(search_pattern)
        return [k.decode('utf-8')[len(prefix):] for k in keys]

    def exists(self, key: str, user_id: Optional[str] = None, workspace_id: Optional[str] = None) -> bool:
        full_key = self._get_namespaced_key(key, user_id, workspace_id)
        return self._redis.exists(full_key) > 0
