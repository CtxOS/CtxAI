import fnmatch
import threading
import time
from typing import Any

_lock = threading.RLock()
_cache: dict[str, dict[str, Any]] = {}
_timestamps: dict[str, dict[str, float]] = {}

_enabled_global: bool = True
_enabled_areas: dict[str, bool] = {}

_max_size: int | None = None
_ttl: float | None = None


def configure(max_size: int | None = None, ttl_seconds: float | None = None) -> None:
    """Set global cache limits. Call once at startup."""
    global _max_size, _ttl
    if max_size is not None:
        _max_size = max_size
    if ttl_seconds is not None:
        _ttl = ttl_seconds


def toggle_global(enabled: bool) -> None:
    global _enabled_global
    _enabled_global = enabled


def toggle_area(area: str, enabled: bool) -> None:
    _enabled_areas[area] = enabled


def has(area: str, key: str) -> bool:
    if not _is_enabled(area):
        return False
    with _lock:
        area_cache = _cache.get(area)
        if area_cache is None or key not in area_cache:
            return False
        if _is_expired(area, key):
            _evict_entry(area, key)
            return False
        return True


def add(area: str, key: str, data: Any) -> None:
    if not _is_enabled(area):
        return
    with _lock:
        if area not in _cache:
            _cache[area] = {}
            _timestamps[area] = {}
        _cache[area][key] = data
        _timestamps[area][key] = time.monotonic()
        _enforce_limits(area)


def get(area: str, key: str, default: Any = None) -> Any:
    if not _is_enabled(area):
        return default
    with _lock:
        area_cache = _cache.get(area)
        if area_cache is None:
            return default
        if _is_expired(area, key):
            _evict_entry(area, key)
            return default
        return area_cache.get(key, default)


def remove(area: str, key: str) -> None:
    if not _is_enabled(area):
        return
    with _lock:
        _evict_entry(area, key)


def clear(area: str) -> None:
    with _lock:
        if any(ch in area for ch in "*?["):
            keys_to_remove = [k for k in _cache.keys() if fnmatch.fnmatch(k, area)]
            for k in keys_to_remove:
                _cache.pop(k, None)
                _timestamps.pop(k, None)
            return

        _cache.pop(area, None)
        _timestamps.pop(area, None)


def clear_all() -> None:
    with _lock:
        _cache.clear()
        _timestamps.clear()


def reset() -> None:
    global _enabled_global, _enabled_areas
    with _lock:
        _cache.clear()
        _timestamps.clear()
    _enabled_areas.clear()
    _enabled_global = True


def cleanup_expired() -> int:
    """Remove all expired entries across all areas. Returns count removed."""
    removed = 0
    with _lock:
        for area in list(_cache.keys()):
            area_ts = _timestamps.get(area, {})
            for key in list(area_ts.keys()):
                if _is_expired(area, key):
                    _evict_entry(area, key)
                    removed += 1
    return removed


def stats() -> dict[str, Any]:
    """Return cache statistics for monitoring."""
    with _lock:
        total_entries = sum(len(area_cache) for area_cache in _cache.values())
        return {
            "areas": len(_cache),
            "total_entries": total_entries,
            "max_size": _max_size,
            "ttl": _ttl,
        }


def _is_expired(area: str, key: str) -> bool:
    if _ttl is None:
        return False
    ts = _timestamps.get(area, {}).get(key)
    if ts is None:
        return True
    return (time.monotonic() - ts) > _ttl


def _evict_entry(area: str, key: str) -> None:
    area_cache = _cache.get(area)
    if area_cache is not None:
        area_cache.pop(key, None)
    area_ts = _timestamps.get(area)
    if area_ts is not None:
        area_ts.pop(key, None)


def _enforce_limits(area: str) -> None:
    area_cache = _cache.get(area)
    if area_cache is None or _max_size is None:
        return
    while len(area_cache) > _max_size:
        area_ts = _timestamps.get(area)
        if area_ts:
            oldest_key = min(area_ts, key=lambda k: area_ts[k])
        else:
            oldest_key = next(iter(area_cache), None)
        if oldest_key is None:
            break
        _evict_entry(area, oldest_key)


def _is_enabled(area: str) -> bool:
    if not _enabled_global:
        return False
    return _enabled_areas.get(area, True)
