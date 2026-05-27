import time
from typing import Any

_cache: dict[str, tuple[Any, float]] = {}
_DEFAULT_TTL = 3600

def tmdb_cache_get(key: str) -> Any | None:
    entry = _cache.get(key)
    if entry is None:
        return None
    val, expiry = entry
    if time.monotonic() > expiry:
        del _cache[key]
        return None
    return val

def tmdb_cache_set(key: str, value: Any, ttl: int | None = None, **kwargs: Any) -> None:
    _cache[key] = (value, time.monotonic() + (ttl or _DEFAULT_TTL))

def tmdb_cache_delete(key: str) -> None:
    _cache.pop(key, None)

def cleanup_redis():
    _cache.clear()
