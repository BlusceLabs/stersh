"""Cache monitoring endpoint."""
from __future__ import annotations

import time
from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db

router = APIRouter(prefix="/cache", tags=["cache"])

@router.get("/stats")
async def cache_stats(
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Get cache statistics."""
    from redis_utils import get_cache_stats as _get_stats

    stats = _get_stats()

    return {
        "timestamp": time.time(),
        "cache": stats,
    }
