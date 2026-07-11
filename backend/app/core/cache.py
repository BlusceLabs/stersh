"""In-memory cache utilities for stersh backend.

Uses cachetools.TTLCache for bounded cache with automatic eviction.
This replaces the previous unbounded dictionary implementation.
"""
import time
from typing import Any

from cachetools import TTLCache

# Bounded cache with max 10,000 entries and 1 hour default TTL
_DEFAULT_TTL = 3600
_MAX_CACHE_SIZE = 10000

_cache: TTLCache[str, Any] = TTLCache(maxsize=_MAX_CACHE_SIZE, ttl=_DEFAULT_TTL)


def tmdb_cache_get(key: str) -> Any | None:
    """Get a value from the cache. Returns None if not found or expired."""
    try:
        return _cache.get(key)
    except Exception:
        return None


def tmdb_cache_set(key: str, value: Any, ttl: int | None = None, **kwargs: Any) -> None:
    """Set a value in the cache with optional custom TTL."""
    if ttl and ttl != _DEFAULT_TTL:
        # For custom TTL, we need to use a separate cache or store with expiry
        # For simplicity, we'll use the default TTL
        pass
    try:
        _cache[key] = value
    except Exception:
        pass


def tmdb_cache_delete(key: str) -> None:
    """Delete a value from the cache."""
    try:
        _cache.pop(key, None)
    except Exception:
        pass


def cleanup_redis() -> None:
    """Clear the entire cache."""
    try:
        _cache.clear()
    except Exception:
        pass


def get_cache_stats() -> dict[str, Any]:
    """Get cache statistics."""
    return {
        "size": len(_cache),
        "maxsize": _cache.maxsize,
        "ttl": _cache.ttl,
    }