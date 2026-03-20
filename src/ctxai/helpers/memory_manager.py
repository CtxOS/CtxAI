"""Unified memory manager with pluggable backends.

Provides a single API for short-term (session) and long-term (persistent)
memory, with support for TTL, importance scoring, and budget-based eviction.

The default backend is an in-memory store suitable for single-process
deployments.  Production backends (Qdrant, Chroma, Redis) can be plugged
in by implementing the ``MemoryBackend`` protocol.

Usage::

    mgr = MemoryManager()
    mgr.remember("user_name", "Alice", importance=0.8, memory_type="long")
    mgr.remember("last_topic", "quantum computing", importance=0.4, memory_type="short", ttl=3600)

    results = mgr.retrieve("Alice", top_k=5, memory_type="long")
    mgr.forget("last_topic", policy="age", max_age_seconds=7200)
    mgr.forget(None, policy="budget", max_entries=100, memory_type="short")
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Memory types & entry
# ---------------------------------------------------------------------------


class MemoryType(str, Enum):
    SHORT = "short"
    LONG = "long"


@dataclass
class MemoryEntry:
    """A single unit of memory."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    key: str = ""
    value: Any = None
    memory_type: MemoryType = MemoryType.SHORT
    importance: float = 0.5  # 0.0 (trivial) → 1.0 (critical)
    topic: str = ""
    source: str = ""
    created_at: float = field(default_factory=time.time)
    accessed_at: float = field(default_factory=time.time)
    access_count: int = 0
    ttl: float = 0.0  # seconds, 0 = no expiry
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        if self.ttl <= 0:
            return False
        return (time.time() - self.created_at) > self.ttl

    def touch(self) -> None:
        self.accessed_at = time.time()
        self.access_count += 1

    def age_seconds(self) -> float:
        return time.time() - self.created_at


# ---------------------------------------------------------------------------
# Backend protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class MemoryBackend(Protocol):
    """Protocol that pluggable backends must satisfy."""

    def store(self, entry: MemoryEntry) -> None: ...
    def get(self, entry_id: str) -> MemoryEntry | None: ...
    def get_by_key(self, key: str, memory_type: MemoryType | None = None) -> MemoryEntry | None: ...
    def search(
        self,
        query: str,
        top_k: int = 5,
        memory_type: MemoryType | None = None,
        min_importance: float = 0.0,
    ) -> list[MemoryEntry]: ...
    def list_all(self, memory_type: MemoryType | None = None) -> list[MemoryEntry]: ...
    def delete(self, entry_id: str) -> bool: ...
    def count(self, memory_type: MemoryType | None = None) -> int: ...
    def clear(self, memory_type: MemoryType | None = None) -> int: ...


# ---------------------------------------------------------------------------
# In-memory backend (default)
# ---------------------------------------------------------------------------


class InMemoryBackend:
    """Simple dict-based backend — fine for single-process, not distributed."""

    def __init__(self) -> None:
        self._entries: dict[str, MemoryEntry] = {}

    def store(self, entry: MemoryEntry) -> None:
        self._entries[entry.id] = entry

    def get(self, entry_id: str) -> MemoryEntry | None:
        return self._entries.get(entry_id)

    def get_by_key(self, key: str, memory_type: MemoryType | None = None) -> MemoryEntry | None:
        for e in self._entries.values():
            if e.key == key and (memory_type is None or e.memory_type == memory_type):
                return e
        return None

    def search(
        self,
        query: str,
        top_k: int = 5,
        memory_type: MemoryType | None = None,
        min_importance: float = 0.0,
    ) -> list[MemoryEntry]:
        query_lower = query.lower()
        scored: list[tuple[float, MemoryEntry]] = []
        for e in self._entries.values():
            if e.is_expired:
                continue
            if memory_type and e.memory_type != memory_type:
                continue
            if e.importance < min_importance:
                continue
            # Simple keyword match scoring
            text = f"{e.key} {e.value}".lower()
            if query_lower in text:
                # Score = importance * recency_boost
                recency = min(1.0, 1.0 / (1.0 + e.age_seconds() / 3600))
                score = e.importance * 0.7 + recency * 0.3
                scored.append((score, e))
        scored.sort(key=lambda x: x[0], reverse=True)
        result = [e for _, e in scored[:top_k]]
        for e in result:
            e.touch()
        return result

    def list_all(self, memory_type: MemoryType | None = None) -> list[MemoryEntry]:
        entries = [
            e
            for e in self._entries.values()
            if not e.is_expired and (memory_type is None or e.memory_type == memory_type)
        ]
        return sorted(entries, key=lambda e: e.importance, reverse=True)

    def delete(self, entry_id: str) -> bool:
        return self._entries.pop(entry_id, None) is not None

    def count(self, memory_type: MemoryType | None = None) -> int:
        return sum(
            1
            for e in self._entries.values()
            if not e.is_expired and (memory_type is None or e.memory_type == memory_type)
        )

    def clear(self, memory_type: MemoryType | None = None) -> int:
        if memory_type is None:
            count = len(self._entries)
            self._entries.clear()
            return count
        to_remove = [eid for eid, e in self._entries.items() if e.memory_type == memory_type]
        for eid in to_remove:
            del self._entries[eid]
        return len(to_remove)


# ---------------------------------------------------------------------------
# Qdrant backend stub
# ---------------------------------------------------------------------------


class QdrantBackend:
    """Qdrant-backed memory store.

    Requires ``qdrant-client`` to be installed.  Falls back to
    ``InMemoryBackend`` if the import fails.
    """

    def __init__(self, url: str = "http://localhost:6333", collection: str = "ctxai_memory"):
        try:
            from qdrant_client import QdrantClient  # type: ignore[import-untyped]
            from qdrant_client.models import Distance, VectorParams  # type: ignore[import-untyped]
        except ImportError:
            logger.warning("qdrant-client not installed, falling back to InMemoryBackend")
            self._fallback = InMemoryBackend()
            self._use_fallback = True
            return

        self._use_fallback = False
        self._client = QdrantClient(url=url)
        self._collection = collection
        self._dim = 384  # default for sentence-transformers/all-MiniLM-L6-v2

        # Ensure collection exists
        collections = [c.name for c in self._client.get_collections().collections]
        if collection not in collections:
            self._client.create_collection(
                collection_name=collection,
                vectors_config=VectorParams(size=self._dim, distance=Distance.COSINE),
            )

    def _delegated(self):
        """Return True if we're using the fallback."""
        return getattr(self, "_use_fallback", True)

    def store(self, entry: MemoryEntry) -> None:
        if self._delegated():
            return self._fallback.store(entry)  # type: ignore
        # Vector embedding would be computed here in a full implementation
        logger.debug(f"QdrantBackend.store({entry.id}) — stub")

    def get(self, entry_id: str) -> MemoryEntry | None:
        if self._delegated():
            return self._fallback.get(entry_id)  # type: ignore
        return None

    def get_by_key(self, key: str, memory_type: MemoryType | None = None) -> MemoryEntry | None:
        if self._delegated():
            return self._fallback.get_by_key(key, memory_type)  # type: ignore
        return None

    def search(
        self,
        query: str,
        top_k: int = 5,
        memory_type: MemoryType | None = None,
        min_importance: float = 0.0,
    ) -> list[MemoryEntry]:
        if self._delegated():
            return self._fallback.search(query, top_k, memory_type, min_importance)  # type: ignore
        return []

    def list_all(self, memory_type: MemoryType | None = None) -> list[MemoryEntry]:
        if self._delegated():
            return self._fallback.list_all(memory_type)  # type: ignore
        return []

    def delete(self, entry_id: str) -> bool:
        if self._delegated():
            return self._fallback.delete(entry_id)  # type: ignore
        return False

    def count(self, memory_type: MemoryType | None = None) -> int:
        if self._delegated():
            return self._fallback.count(memory_type)  # type: ignore
        return 0

    def clear(self, memory_type: MemoryType | None = None) -> int:
        if self._delegated():
            return self._fallback.clear(memory_type)  # type: ignore
        return 0


# ---------------------------------------------------------------------------
# Memory manager
# ---------------------------------------------------------------------------


class MemoryManager:
    """High-level memory API.

    Delegates storage to a pluggable ``MemoryBackend`` and adds TTL
    enforcement, importance-based eviction, and budget controls.
    """

    def __init__(self, backend: MemoryBackend | None = None) -> None:
        self._backend: MemoryBackend = backend or InMemoryBackend()

    @property
    def backend(self) -> MemoryBackend:
        return self._backend

    # -- write --------------------------------------------------------------

    def remember(
        self,
        key: str,
        value: Any,
        importance: float = 0.5,
        memory_type: str | MemoryType = MemoryType.SHORT,
        topic: str = "",
        source: str = "",
        ttl: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        """Store a memory entry.

        If an entry with the same *key* and *memory_type* already exists
        it is updated (upsert).
        """
        mt = MemoryType(memory_type) if isinstance(memory_type, str) else memory_type

        # Upsert: update existing key
        existing = self._backend.get_by_key(key, mt)
        if existing:
            existing.value = value
            existing.importance = importance
            existing.topic = topic or existing.topic
            existing.source = source or existing.source
            existing.ttl = ttl or existing.ttl
            existing.metadata = metadata or existing.metadata
            existing.touch()
            self._backend.store(existing)
            return existing

        entry = MemoryEntry(
            key=key,
            value=value,
            memory_type=mt,
            importance=max(0.0, min(1.0, importance)),
            topic=topic,
            source=source,
            ttl=ttl,
            metadata=metadata or {},
        )
        self._backend.store(entry)
        return entry

    # -- read ---------------------------------------------------------------

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        memory_type: str | MemoryType | None = None,
        min_importance: float = 0.0,
    ) -> list[MemoryEntry]:
        """Search memory entries by keyword match, ranked by importance × recency."""
        mt = MemoryType(memory_type) if isinstance(memory_type, str) else memory_type
        return self._backend.search(query, top_k=top_k, memory_type=mt, min_importance=min_importance)

    def get(self, key: str, memory_type: str | MemoryType | None = None) -> MemoryEntry | None:
        mt = MemoryType(memory_type) if isinstance(memory_type, str) else memory_type
        entry = self._backend.get_by_key(key, mt)
        if entry and not entry.is_expired:
            entry.touch()
            return entry
        return None

    def list_all(self, memory_type: str | MemoryType | None = None) -> list[MemoryEntry]:
        mt = MemoryType(memory_type) if isinstance(memory_type, str) else memory_type
        return self._backend.list_all(mt)

    # -- forget -------------------------------------------------------------

    def forget(
        self,
        key: str | None = None,
        policy: str = "exact",
        memory_type: str | MemoryType | None = None,
        max_age_seconds: float = 0,
        max_entries: int = 0,
        min_importance: float = 0.0,
    ) -> int:
        """Remove entries by policy.

        Policies:
          - ``exact``: delete the entry with the given *key*.
          - ``age``: delete entries older than *max_age_seconds*.
          - ``budget``: keep at most *max_entries*, evicting lowest-importance first.
          - ``importance``: delete entries with importance ≤ *min_importance*.
          - ``expired``: delete all TTL-expired entries (the default housekeeping).
        """
        mt = MemoryType(memory_type) if isinstance(memory_type, str) else memory_type
        removed = 0

        if policy == "exact" and key:
            entry = self._backend.get_by_key(key, mt)
            if entry:
                self._backend.delete(entry.id)
                removed = 1

        elif policy == "age" and max_age_seconds > 0:
            cutoff = time.time() - max_age_seconds
            for e in self._backend.list_all(mt):
                if e.created_at < cutoff:
                    self._backend.delete(e.id)
                    removed += 1

        elif policy == "budget" and max_entries > 0:
            entries = self._backend.list_all(mt)
            if len(entries) > max_entries:
                # Sort by importance ascending → evict lowest importance
                entries.sort(key=lambda e: e.importance)
                to_evict = entries[: len(entries) - max_entries]
                for e in to_evict:
                    self._backend.delete(e.id)
                    removed += 1

        elif policy == "importance":
            for e in self._backend.list_all(mt):
                if e.importance <= min_importance:
                    self._backend.delete(e.id)
                    removed += 1

        elif policy == "expired":
            for e in self._backend.list_all(mt):
                if e.is_expired:
                    self._backend.delete(e.id)
                    removed += 1

        return removed

    # -- maintenance --------------------------------------------------------

    def purge_expired(self) -> int:
        """Remove all TTL-expired entries.  Safe to call periodically."""
        return self.forget(policy="expired")

    def enforce_budget(self, max_short: int = 500, max_long: int = 2000) -> None:
        """Apply budget limits to both memory types."""
        self.forget(policy="budget", memory_type=MemoryType.SHORT, max_entries=max_short)
        self.forget(policy="budget", memory_type=MemoryType.LONG, max_entries=max_long)

    def stats(self) -> dict[str, Any]:
        """Return memory usage statistics."""
        short = self._backend.count(MemoryType.SHORT)
        long = self._backend.count(MemoryType.LONG)
        return {
            "short_term_count": short,
            "long_term_count": long,
            "total": short + long,
        }
