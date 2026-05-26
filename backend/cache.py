"""Cache monitoring endpoint."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any
import time

router = APIRouter(prefix="/cache", tags=["cache"])

@router.get("/stats")
async def cache_stats(
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Get cache statistics."""
    # Get Redis stats if available
    try:
        from .redis_utils import get_redis_client
        client = get_redis_client()
        info = client.info()
        memory = info.get("used_memory_human", "unknown")
        connected_clients = info.get("connected_clients", 0)
    except Exception:
        memory = "unknown"
        connected_clients = 0
    
    return {
        "timestamp": time.time(),
        "redis": {
            "connected": connected_clients > 0,
            "memory_usage": memory,
            "connected_clients": connected_clients,
        },
        "cache_hits": 0,  # Would need to track this
        "cache_misses": 0,
        "cache_hit_ratio": 0.0,
    }