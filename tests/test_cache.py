import pytest
from ctxai.helpers import cache


@pytest.fixture(autouse=True)
def reset_cache():
    cache.reset()
    yield
    cache.reset()


class TestCache:
    def test_cache_toggle_global(self):
        cache.toggle_global(True)
        assert cache._enabled_global is True

    def test_cache_toggle_global_false(self):
        cache.toggle_global(False)
        assert cache._enabled_global is False

    def test_cache_toggle_area(self):
        cache.toggle_area("test_area", True)
        assert cache._enabled_areas.get("test_area") is True

    def test_cache_has_returns_false_when_disabled(self):
        cache.toggle_global(False)
        result = cache.has("area", "key")
        assert result is False
        cache.toggle_global(True)

    def test_cache_add_and_has(self):
        cache.add("test_area", "test_key", "test_value")
        result = cache.has("test_area", "test_key")
        assert result is True

    def test_cache_get(self):
        cache.add("test_area", "test_key", "test_value")
        result = cache.get("test_area", "test_key")
        assert result == "test_value"

    def test_cache_clear_all(self):
        cache.add("area1", "key1", "value1")
        cache.add("area2", "key2", "value2")
        cache.clear_all()
        assert cache.has("area1", "key1") is False
        assert cache.has("area2", "key2") is False
