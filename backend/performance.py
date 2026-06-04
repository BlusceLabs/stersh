"""Performance monitoring for watchfy backend."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any
import time
import os
from datetime import datetime, timezone
from database import get_db

router = APIRouter(prefix="/performance", tags=["performance"])

@router.get("/")
async def get_performance_metrics(
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Get real-time performance metrics."""
    # Get database stats
    try:
        db_stats = db.execute("PRAGMA stats;").fetchall()
    except Exception:
        db_stats = []
    
    return {
        "timestamp": time.time(),
        "server_time": datetime.now(timezone.utc).isoformat(),
        "database": {
            "connections": "N/A",  # Would need specific DB driver info
            "stats": [dict(row) for row in db_stats] if db_stats else [],
        },
        "memory": {
            "rss": os.statvfs('/').f_blocks if os.path.exists('/') else 0,
        },
        "cpu": {
            "load": 0,  # Placeholder
        },
        "uptime": time.time(),
    }