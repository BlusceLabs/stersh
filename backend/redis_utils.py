# Redis utilities for TMDB caching
from typing import Any

redis_client = None
redis_pool = None

def tmdb_cache_get(key: str) -> Any | None:
    """Get cached TMDB response by key."""
    return None

def tmdb_cache_set(key: str, value: Any, **kwargs: Any) -> None:
    """Cache TMDB response."""
    pass

def tmdb_cache_delete(key: str) -> None:
    """Delete cached TMDB response."""
    pass

def cleanup_redis():
    """Cleanup Redis connection pool."""
    global redis_client, redis_pool
    if redis_client is not None:
        redis_client.close()
        redis_client = None
    if redis_pool is not None:
        redis_pool.disconnect()
        redis_pool = None