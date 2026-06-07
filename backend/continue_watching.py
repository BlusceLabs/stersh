"""Continue Watching router — playback progress tracking for watchfy backend."""
from __future__ import annotations

from typing import Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db, PlaybackHistory, User
from auth import get_current_active_user

router = APIRouter(prefix="/continue-watching", tags=["continue-watching"])


class ProgressIn(BaseModel):
    tmdb_id: int = Field(gt=0)
    media_type: str  # 'movie' or 'tv'
    season: Optional[int] = Field(default=None, ge=1)
    episode: Optional[int] = Field(default=None, ge=1)
    title: Optional[str] = Field(default=None, max_length=500)
    poster_path: Optional[str] = Field(default=None, max_length=500)
    source_server: Optional[str] = Field(default=None, max_length=32)
    current_time: float = Field(default=0, ge=0)
    duration: float = Field(default=0, ge=0)


class ProgressOut(BaseModel):
    tmdb_id: int
    media_type: str
    title: str = ""
    poster_path: str = ""
    season: Optional[int] = None
    episode: Optional[int] = None
    current_time: float
    duration: float
    progress_pct: float
    updated_at: Optional[str] = None


@router.get("/", response_model=list[ProgressOut])
async def get_continue_watching(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> list[ProgressOut]:
    """Get user's continue-watching list, deduplicated by tmdb_id (one entry per show/movie)."""
    rows = (
        db.query(PlaybackHistory)
        .filter(PlaybackHistory.user_id == current_user.id)
        .filter(PlaybackHistory.current_time > 0)
        .order_by(PlaybackHistory.updated_at.desc())
        .all()
    )
    seen: dict[tuple, bool] = {}
    result: list[ProgressOut] = []
    for r in rows:
        key = (r.tmdb_id, r.media_type)
        if key in seen:
            continue
        seen[key] = True
        pct = round(r.current_time / r.duration * 100, 2) if r.duration and r.duration > 0 else 0
        result.append(ProgressOut(
            tmdb_id=r.tmdb_id,
            media_type=r.media_type,
            title=r.title or "",
            poster_path=r.poster_path or "",
            season=r.season,
            episode=r.episode,
            current_time=r.current_time,
            duration=r.duration,
            progress_pct=pct,
            updated_at=r.updated_at.isoformat() if r.updated_at else None,
        ))
        if len(result) >= 20:
            break
    return result


_ALLOWED_SOURCE_SERVERS = frozenset({"white", "black"})


@router.post("/")
async def save_progress(
    body: ProgressIn,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Save or update playback progress for the current user."""
    if body.media_type not in ("movie", "tv"):
        raise HTTPException(status_code=400, detail="media_type must be 'movie' or 'tv'")
    server = body.source_server
    if server is not None and server not in _ALLOWED_SOURCE_SERVERS:
        raise HTTPException(status_code=400, detail="source_server must be 'white' or 'black'")

    progress_pct = round(body.current_time / body.duration * 100, 2) if body.duration and body.duration > 0 else 0

    row = (
        db.query(PlaybackHistory)
        .filter(PlaybackHistory.user_id == current_user.id)
        .filter(PlaybackHistory.tmdb_id == body.tmdb_id)
        .filter(PlaybackHistory.media_type == body.media_type)
    )
    if body.season is not None:
        row = row.filter(PlaybackHistory.season == body.season)
    else:
        row = row.filter(PlaybackHistory.season.is_(None))
    if body.episode is not None:
        row = row.filter(PlaybackHistory.episode == body.episode)
    else:
        row = row.filter(PlaybackHistory.episode.is_(None))
    row = row.first()

    if row:
        row.current_time = body.current_time
        row.duration = body.duration
        row.progress_pct = progress_pct
        row.title = body.title or row.title
        row.poster_path = body.poster_path or row.poster_path
        row.source_server = server or row.source_server
        row.updated_at = datetime.now(timezone.utc)
    else:
        row = PlaybackHistory(
            user_id=current_user.id,
            tmdb_id=body.tmdb_id,
            media_type=body.media_type,
            title=body.title,
            poster_path=body.poster_path,
            season=body.season,
            episode=body.episode,
            current_time=body.current_time,
            duration=body.duration,
            progress_pct=progress_pct,
            source_server=server,
        )
        db.add(row)

    db.commit()
    db.refresh(row)

    return {
        "message": "Progress saved",
        "tmdb_id": body.tmdb_id,
        "media_type": body.media_type,
        "season": body.season,
        "episode": body.episode,
        "progress_pct": progress_pct,
    }


@router.delete("/{tmdb_id}")
async def remove_from_continue_watching(
    tmdb_id: int,
    media_type: str = "movie",
    season: Optional[int] = None,
    episode: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Remove an item from continue watching."""
    if media_type not in ("movie", "tv"):
        raise HTTPException(status_code=400, detail="media_type must be 'movie' or 'tv'")
    if season is not None and season < 1:
        raise HTTPException(status_code=400, detail="season must be >= 1")
    if episode is not None and episode < 1:
        raise HTTPException(status_code=400, detail="episode must be >= 1")
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
