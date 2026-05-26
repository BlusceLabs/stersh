"""Configuration endpoint."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any
import os

router = APIRouter(prefix="/config", tags=["config"])

@router.get("/")
async def get_config(
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Get current configuration."""
    config = {
        "database_url": os.environ.get("DATABASE_URL", "sqlite:///watchfy.db"),
        "redis_url": os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
        "tmdb_api_key": os.environ.get("TMDB_API_KEY", "hidden"),
        "jwt_secret": os.environ.get("JWT_SECRET", "hidden"),
        "ffmpeg_path": os.environ.get("FFMPEG_BIN", "ffmpeg"),
        "environment": os.environ.get("ENV", "development"),
        "debug": os.environ.get("DEBUG", "false").lower() == "true",
        "host": os.environ.get("HOST", "0.0.0.0"),
        "port": os.environ.get("PORT", "8000"),
        "database_pool_size": os.environ.get("DB_POOL_SIZE", "10"),
        "redis_pool_size": os.environ.get("REDIS_POOL_SIZE", "10"),
    }
    return config