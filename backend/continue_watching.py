"""Continue Watching router — playback progress tracking for watchfy backend."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db, PlaybackHistory, User
from auth import get_current_active_user

router = APIRouter(prefix="/continue-watching", tags=["continue-watching"])


class ProgressIn(BaseModel):
    tmdb_id: int
    media_type: str  # 'movie' or 'tv'
    season: Optional[int] = None
    episode: Optional[int] = None
    current_time: float = 0
    duration: float = 0


class ProgressOut(BaseModel):
    tmdb_id: int
    media_type: str
    season: Optional[int] = None
    episode: Optional[int] = None
    current_time: float
    duration: float
    progress_pct: float
    updated_at: str


@router.get("/", response_model=List[ProgressOut])
async def get_continue_watching(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Get user's continue-watching list, sorted by most recently updated."""
    rows = (
        db.query(PlaybackHistory)
        .filter(PlaybackHistory.user_id == current_user.id)
        .filter(PlaybackHistory.current_time > 0)
        .order_by(PlaybackHistory.updated_at.desc())
        .limit(20)
        .all()
    )
    result = []
    for r in rows:
        pct = round(r.current_time / r.duration * 100, 2) if r.duration and r.duration > 0 else 0
        result.append({
            "tmdb_id": r.tmdb_id,
            "media_type": r.media_type,
            "season": r.season,
            "episode": r.episode,
            "current_time": r.current_time,
            "duration": r.duration,
            "progress_pct": pct,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        })
    return result


@router.post("/")
async def save_progress(
    body: ProgressIn,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Save or update playback progress for the current user."""
    if body.media_type not in ("movie", "tv"):
        raise HTTPException(status_code=400, detail="media_type must be 'movie' or 'tv'")

    # Upsert: check for existing row
    row = (
        db.query(PlaybackHistory)
        .filter(PlaybackHistory.user_id == current_user.id)
        .filter(PlaybackHistory.tmdb_id == body.tmdb_id)
        .filter(PlaybackHistory.media_type == body.media_type)
    )
    if body.season is not None:
        row = row.filter(PlaybackHistory.season == body.season)
    if body.episode is not None:
        row = row.filter(PlaybackHistory.episode == body.episode)
    row = row.first()

    if row:
        row.current_time = body.current_time
        row.duration = body.duration
        row.updated_at = datetime.utcnow()
    else:
        row = PlaybackHistory(
            user_id=current_user.id,
            tmdb_id=body.tmdb_id,
            media_type=body.media_type,
            season=body.season,
            episode=body.episode,
            current_time=body.current_time,
            duration=body.duration,
        )
        db.add(row)

    db.commit()
    db.refresh(row)

    pct = round(body.current_time / body.duration * 100, 2) if body.duration and body.duration > 0 else 0
    return {
        "message": "Progress saved",
        "tmdb_id": body.tmdb_id,
        "media_type": body.media_type,
        "progress_pct": pct,
    }


@router.delete("/{tmdb_id}")
async def remove_from_continue_watching(
    tmdb_id: int,
    media_type: str = "movie",
    season: Optional[int] = None,
    episode: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    """Remove an item from continue watching."""
    q = (
        db.query(PlaybackHistory)
        .filter(PlaybackHistory.user_id == current_user.id)
        .filter(PlaybackHistory.tmdb_id == tmdb_id)
        .filter(PlaybackHistory.media_type == media_type)
    )
    if season is not None:
        q = q.filter(PlaybackHistory.season == season)
    if episode is not None:
        q = q.filter(PlaybackHistory.episode == episode)
    row = q.first()
    if row:
        db.delete(row)
        db.commit()
    return {"message": "Removed"}
