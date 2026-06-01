"""Safe configuration endpoint."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any
import os

from database import get_db

router = APIRouter(prefix="/api/config", tags=["config"])

def _configured(name: str) -> bool:
    return bool(os.environ.get(name))

@router.get("/")
async def get_config(
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Get current configuration."""
    config = {
        "database": "configured" if _configured("DATABASE_URL") else "sqlite-default",
        "redis": "configured" if _configured("REDIS_URL") else "memory-cache",
        "tmdb_api_key": "configured" if _configured("TMDB_API_KEY") else "missing",
        "jwt_secret": "configured" if _configured("JWT_SECRET") else "development-default",
        "ffmpeg_path": os.environ.get("FFMPEG_BIN", "ffmpeg"),
        "environment": os.environ.get("ENV", "development"),
        "debug": os.environ.get("DEBUG", "false").lower() == "true",
        "host": os.environ.get("HOST", "0.0.0.0"),
        "port": os.environ.get("PORT", "8000"),
        "database_pool_size": os.environ.get("DB_POOL_SIZE", "10"),
        "redis_pool_size": os.environ.get("REDIS_POOL_SIZE", "10"),
    }
    return config
