"""Performance monitoring for watchfy backend."""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db

router = APIRouter(prefix="/performance", tags=["performance"])

@router.get("/")
async def get_performance_metrics(
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Get real-time performance metrics."""
    return {
        "timestamp": time.time(),
        "server_time": datetime.now(timezone.utc).isoformat(),
        "uptime": time.time(),
        "pid": os.getpid(),
    }
