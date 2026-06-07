"""Database monitoring endpoint."""
from __future__ import annotations

import time
from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import (
    get_db, Movie, TVShow, User, Favorite, Watchlist,
    PlaybackHistory, Rating,
)

router = APIRouter(prefix="/db", tags=["database"])

@router.get("/stats")
async def database_stats(
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Get database statistics."""
    # Get table row counts
    movies_count = db.query(Movie).count()
    tv_shows_count = db.query(TVShow).count()
    users_count = db.query(User).count()
    favorites_count = db.query(Favorite).count()
    watchlists_count = db.query(Watchlist).count()
    history_count = db.query(PlaybackHistory).count()
    ratings_count = db.query(Rating).count()
    
    return {
        "tables": {
            "movies": movies_count,
            "tv_shows": tv_shows_count,
            "users": users_count,
            "favorites": favorites_count,
            "watchlists": watchlists_count,
            "playback_history": history_count,
            "ratings": ratings_count,
        },
        "timestamp": time.time(),
    }