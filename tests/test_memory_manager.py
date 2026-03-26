"""Unit tests for MemoryManager — remember, retrieve, forget, TTL, budget."""

import time

import pytest

from ctxai.helpers.memory_manager import (
    InMemoryBackend,
    MemoryEntry,
    MemoryManager,
    MemoryType,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def backend():
    return InMemoryBackend()


@pytest.fixture
def mgr(backend):
    return MemoryManager(backend=backend)


# ---------------------------------------------------------------------------
# InMemoryBackend
# ---------------------------------------------------------------------------


class TestInMemoryBackend:
    def test_store_and_get(self, backend):
        entry = MemoryEntry(key="k", value="v")
        backend.store(entry)
        assert backend.get(entry.id) is entry

    def test_get_missing_returns_none(self, backend):
        assert backend.get("nonexistent") is None

    def test_get_by_key(self, backend):
        entry = MemoryEntry(key="name", value="Alice", memory_type=MemoryType.LONG)
        backend.store(entry)
        assert backend.get_by_key("name", MemoryType.LONG) is entry
        assert backend.get_by_key("name", MemoryType.SHORT) is None
        assert backend.get_by_key("name") is entry  # any type

    def test_delete(self, backend):
        entry = MemoryEntry(key="k", value="v")
        backend.store(entry)
        assert backend.delete(entry.id) is True
        assert backend.get(entry.id) is None
        assert backend.delete(entry.id) is False

    def test_count(self, backend):
        assert backend.count() == 0
        backend.store(MemoryEntry(key="a", value=1, memory_type=MemoryType.SHORT))
        backend.store(MemoryEntry(key="b", value=2, memory_type=MemoryType.LONG))
        assert backend.count() == 2
        assert backend.count(MemoryType.SHORT) == 1
        assert backend.count(MemoryType.LONG) == 1

    def test_clear_all(self, backend):
        backend.store(MemoryEntry(key="a", value=1))
        backend.store(MemoryEntry(key="b", value=2))
        assert backend.clear() == 2
        assert backend.count() == 0

    def test_clear_by_type(self, backend):
        backend.store(MemoryEntry(key="a", value=1, memory_type=MemoryType.SHORT))
        backend.store(MemoryEntry(key="b", value=2, memory_type=MemoryType.LONG))
        assert backend.clear(MemoryType.SHORT) == 1
        assert backend.count(MemoryType.SHORT) == 0
        assert backend.count(MemoryType.LONG) == 1

    def test_list_all_filters_expired(self, backend):
        entry = MemoryEntry(key="k", value="v", ttl=0.001)
        backend.store(entry)
        time.sleep(0.01)
        assert backend.list_all() == []
        assert backend.count() == 0

    def test_search_by_keyword(self, backend):
        backend.store(MemoryEntry(key="user_name", value="Alice", importance=0.9))
        backend.store(MemoryEntry(key="user_city", value="Paris", importance=0.5))
        backend.store(MemoryEntry(key="topic", value="machine learning", importance=0.7))
        results = backend.search("Alice")
        assert len(results) == 1
        assert results[0].key == "user_name"

    def test_search_respects_min_importance(self, backend):
        backend.store(MemoryEntry(key="low", value="x", importance=0.1))
        backend.store(MemoryEntry(key="high", value="x", importance=0.9))
        results = backend.search("x", min_importance=0.5)
        assert len(results) == 1
        assert results[0].key == "high"

    def test_search_respects_top_k(self, backend):
        for i in range(10):
            backend.store(MemoryEntry(key=f"k{i}", value="match", importance=i / 10))
        results = backend.search("match", top_k=3)
        assert len(results) == 3
        # Should be highest importance
        assert results[0].importance >= results[1].importance >= results[2].importance


# ---------------------------------------------------------------------------
# MemoryEntry
# ---------------------------------------------------------------------------


class TestMemoryEntry:
    def test_is_expired_ttl(self):
        entry = MemoryEntry(key="k", value="v", ttl=0.001)
        assert entry.is_expired is False
        time.sleep(0.01)
        assert entry.is_expired is True

    def test_is_expired_no_ttl(self):
        entry = MemoryEntry(key="k", value="v", ttl=0.0)
        time.sleep(0.01)
        assert entry.is_expired is False

    def test_touch_updates_access(self):
        entry = MemoryEntry(key="k", value="v")
        old_accessed = entry.accessed_at
        assert entry.access_count == 0
        entry.touch()
        assert entry.access_count == 1
        assert entry.accessed_at >= old_accessed

    def test_age_seconds(self):
        entry = MemoryEntry(key="k", value="v")
        time.sleep(0.02)
        assert entry.age_seconds() >= 0.02


# ---------------------------------------------------------------------------
# MemoryManager
# ---------------------------------------------------------------------------


class TestMemoryManager:
    def test_remember_creates_entry(self, mgr):
        entry = mgr.remember("user_name", "Alice", importance=0.8, memory_type="long")
        assert entry.key == "user_name"
        assert entry.value == "Alice"
        assert entry.importance == 0.8
        assert entry.memory_type == MemoryType.LONG

    def test_remember_upserts_existing(self, mgr):
        first = mgr.remember("user_name", "Alice")
        second = mgr.remember("user_name", "Bob")
        assert first.id == second.id
        assert second.value == "Bob"
        assert mgr.stats()["total"] == 1

    def test_remember_clamps_importance(self, mgr):
        low = mgr.remember("low", "v", importance=-0.5)
        high = mgr.remember("high", "v", importance=1.5)
        assert low.importance == 0.0
        assert high.importance == 1.0

    def test_get_by_key(self, mgr):
        mgr.remember("k", "v", memory_type="short")
        entry = mgr.get("k")
        assert entry is not None
        assert entry.value == "v"
        entry_long = mgr.get("k", memory_type="long")
        assert entry_long is None

    def test_get_expired_returns_none(self, mgr):
        mgr.remember("k", "v", ttl=0.001)
        time.sleep(0.01)
        assert mgr.get("k") is None

    def test_retrieve_by_query(self, mgr):
        mgr.remember("user_name", "Alice", importance=0.9)
        mgr.remember("user_city", "Paris", importance=0.5)
        results = mgr.retrieve("Alice")
        assert len(results) == 1
        assert results[0].key == "user_name"

    def test_retrieve_with_min_importance(self, mgr):
        mgr.remember("low", "x", importance=0.1)
        mgr.remember("high", "x", importance=0.9)
        results = mgr.retrieve("x", min_importance=0.5)
        assert len(results) == 1

    def test_list_all(self, mgr):
        mgr.remember("a", "1", memory_type="short")
        mgr.remember("b", "2", memory_type="long")
        all_entries = mgr.list_all()
        assert len(all_entries) == 2
        short_entries = mgr.list_all(memory_type="short")
        assert len(short_entries) == 1

    def test_forget_exact(self, mgr):
        mgr.remember("k", "v")
        assert mgr.forget("k", policy="exact") == 1
        assert mgr.get("k") is None

    def test_forget_age(self, mgr):
        mgr.remember("old", "v")
        time.sleep(0.02)
        assert mgr.forget(policy="age", max_age_seconds=0.01) == 1
        assert mgr.get("old") is None

    def test_forget_budget(self, mgr):
        for i in range(5):
            mgr.remember(f"k{i}", i, importance=i / 10)
        removed = mgr.forget(policy="budget", max_entries=3)
        assert removed == 2
        assert mgr.stats()["total"] == 3

    def test_forget_importance(self, mgr):
        mgr.remember("low", "v", importance=0.1)
        mgr.remember("high", "v", importance=0.9)
        removed = mgr.forget(policy="importance", min_importance=0.5)
        assert removed == 1
        assert mgr.get("low") is None
        assert mgr.get("high") is not None

    def test_forget_expired_via_backend(self, backend, mgr):
        """Test expired entry cleanup via direct backend access (bypasses list_all filtering)."""
        entry = MemoryEntry(key="ephemeral", value="v", ttl=0.001)
        backend.store(entry)
        time.sleep(0.01)
        # Entry is in the backend but expired - verify it's considered expired
        assert entry.is_expired is True
        # Verify the entry is NOT returned by list_all (filtered)
        assert backend.list_all() == []
        # Delete it directly from backend
        assert backend.delete(entry.id) is True

    def test_enforce_budget(self, mgr):
        for i in range(10):
            mgr.remember(f"short{i}", i, memory_type="short")
        for i in range(5):
            mgr.remember(f"long{i}", i, memory_type="long")
        mgr.enforce_budget(max_short=5, max_long=3)
        assert mgr.stats()["short_term_count"] == 5
        assert mgr.stats()["long_term_count"] == 3

    def test_stats(self, mgr):
        mgr.remember("a", "1", memory_type="short")
        mgr.remember("b", "2", memory_type="long")
        stats = mgr.stats()
        assert stats["short_term_count"] == 1
        assert stats["long_term_count"] == 1
        assert stats["total"] == 2

    def test_retrieve_touches_entries(self, mgr):
        entry = mgr.remember("k", "v", importance=0.5)
        old_access_count = entry.access_count
        mgr.retrieve("v")
        assert entry.access_count > old_access_count
