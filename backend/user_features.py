"""User features router for favorites, watchlist, history, and ratings."""
from __future__ import annotations

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .database import get_db, Favorite, Watchlist, PlaybackHistory, Rating, Movie, TVShow
from .auth import get_current_active_user

router = APIRouter(prefix="/user", tags=["user-features"])

# ── Favorites ──────────────────────────────────────────────────────────────────

@router.post("/favorites/{media_type}/{tmdb_id}")
async def add_favorite(
    media_type: str,
    tmdb_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Add a movie/TV show to user's favorites."""
    if media_type not in ("movie", "tv"):
        raise HTTPException(status_code=400, detail="media_type must be 'movie' or 'tv'")
    
    # Check if already favorited
    fav = db.query(Favorite).filter(
        Favorite.user_id == current_user.id,
        Favorite.tmdb_id == tmdb_id,
        Favorite.media_type == media_type
    ).first()
    if fav:
        raise HTTPException(status_code=400, detail="Already in favorites")
    
    favorite = Favorite(
        user_id=current_user.id,
        tmdb_id=tmdb_id,
        media_type=media_type
    )
    db.add(favorite)
    db.commit()
    db.refresh(favorite)
    
    return {"message": "Added to favorites", "favorite": favorite}

@router.get("/favorites")
async def get_favorites(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Get user's favorite movies and TV shows."""
    favorites = db.query(Favorite).filter(
        Favorite.user_id == current_user.id
    ).order_by(Favorite.created_at.desc()).all()
    
    # Separate movies and TV shows
    movies = []
    tv_shows = []
    for fav in favorites:
        if fav.media_type == "movie":
            movies.append(fav)
        else:
            tv_shows.append(fav)
    
    return {
        "movies": movies,
        "tv_shows": tv_shows,
        "total": len(favorites)
    }

@router.delete("/favorites/{media_type}/{tmdb_id}")
async def remove_favorite(
    media_type: str,
    tmdb_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Remove a movie/TV show from user's favorites."""
    fav = db.query(Favorite).filter(
        Favorite.user_id == current_user.id,
        Favorite.tmdb_id == tmdb_id,
        Favorite.media_type == media_type
    ).first()
    
    if not fav:
        raise HTTPException(status_code=404, detail="Not in favorites")
    
    db.delete(fav)
    db.commit()
    
    return {"message": "Removed from favorites"}

# ── Watchlist ───────────────────────────────────────────────────────────────────

@router.post("/watchlist/{media_type}/{tmdb_id}")
async def add_to_watchlist(
    media_type: str,
    tmdb_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Add a movie/TV show to user's watchlist."""
    if media_type not in ("movie", "tv"):
        raise HTTPException(status_code=400, detail="media_type must be 'movie' or 'tv'")
    
    # Check if already in watchlist
    wl = db.query(Watchlist).filter(
        Watchlist.user_id == current_user.id,
        Watchlist.tmdb_id == tmdb_id,
        Watchlist.media_type == media_type
    ).first()
    if wl:
        raise HTTPException(status_code=400, detail="Already in watchlist")
    
    watchlist_item = Watchlist(
        user_id=current_user.id,
        tmdb_id=tmdb_id,
        media_type=media_type,
        watched=False
    )
    db.add(watchlist_item)
    db.commit()
    db.refresh(watchlist_item)
    
    return {"message": "Added to watchlist", "watchlist_item": watchlist_item}

@router.get("/watchlist")
async def get_watchlist(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Get user's watchlist."""
    watchlist = db.query(Watchlist).filter(
        Watchlist.user_id == current_user.id
    ).order_by(Watchlist.created_at.desc()).all()
    
    # Separate movies and TV shows
    movies = []
    tv_shows = []
    for item in watchlist:
        if item.media_type == "movie":
            movies.append(item)
        else:
            tv_shows.append(item)
    
    return {
        "movies": movies,
        "tv_shows": tv_shows,
        "total": len(watchlist)
    }

@router.patch("/watchlist/{media_type}/{tmdb_id}/watched")
async def mark_watched(
    media_type: str,
    tmdb_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Mark a movie/TV show as watched."""
    wl = db.query(Watchlist).filter(
        Watchlist.user_id == current_user.id,
        Watchlist.tmdb_id == tmdb_id,
        Watchlist.media_type == media_type
    ).first()
    
    if not wl:
        raise HTTPException(status_code=404, detail="Item not found in watchlist")
    
    wl.watched = True
    db.commit()
    db.refresh(wl)
    
    return {"message": "Marked as watched", "watchlist_item": wl}

@router.delete("/watchlist/{media_type}/{tmdb_id}")
async def remove_from_watchlist(
    media_type: str,
    tmdb_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Remove a movie/TV show from watchlist."""
    wl = db.query(Watchlist).filter(
        Watchlist.user_id == current_user.id,
        Watchlist.tmdb_id == tmdb_id,
        Watchlist.media_type == media_type
    ).first()
    
    if not wl:
        raise HTTPException(status_code=404, detail="Not in watchlist")
    
    db.delete(wl)
    db.commit()
    
    return {"message": "Removed from watchlist"}

# ── Playback History ────────────────────────────────────────────────────────────

@router.post("/history")
async def add_playback_history(
    media_type: str,
    tmdb_id: int,
    season: int | None = None,
    episode: int | None = None,
    progress: int = 0,  # in seconds
    total_duration: int | None = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Add playback history entry."""
    if media_type not in ("movie", "tv"):
        raise HTTPException(status_code=400, detail="media_type must be 'movie' or 'tv'")
    
    # Check if entry exists for today (allow multiple entries per day)
    history = db.query(PlaybackHistory).filter(
        PlaybackHistory.user_id == current_user.id,
        PlaybackHistory.tmdb_id == tmdb_id,
        PlaybackHistory.media_type == media_type,
        PlaybackHistory.season == season,
        PlaybackHistory.episode == episode,
    ).first()
    
    if history:
        # Update existing entry
        history.progress = progress
        history.total_duration = total_duration
        history.watched_at = datetime.now()
    else:
        # Create new entry
        history = PlaybackHistory(
            user_id=current_user.id,
            tmdb_id=tmdb_id,
            media_type=media_type,
            season=season,
            episode=episode,
            progress=progress,
            total_duration=total_duration,
        )
        db.add(history)
    
    db.commit()
    db.refresh(history)
    
    return {"message": "History updated", "history": history}

@router.get("/history")
async def get_playback_history(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Get user's playback history."""
    history = db.query(PlaybackHistory).filter(
        PlaybackHistory.user_id == current_user.id
    ).order_by(PlaybackHistory.watched_at.desc()).all()
    
    # Group by media type
    movies = []
    tv_shows = []
    for item in history:
        if item.media_type == "movie":
            movies.append(item)
        else:
            tv_shows.append(item)
    
    return {
        "movies": movies,
        "tv_shows": tv_shows,
        "total": len(history)
    }

# ── Ratings ─────────────────────────────────────────────────────────────────────

@router.post("/ratings/{media_type}/{tmdb_id}")
async def add_rating(
    media_type: str,
    tmdb_id: int,
    rating: int,
    review: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Add or update rating for a movie/TV show."""
    if media_type not in ("movie", "tv"):
        raise HTTPException(status_code=400, detail="media_type must be 'movie' or 'tv'")
    
    if not (1 <= rating <= 5):
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    
    # Check if rating exists
    existing = db.query(Rating).filter(
        Rating.user_id == current_user.id,
        Rating.tmdb_id == tmdb_id,
        Rating.media_type == media_type
    ).first()
    
    if existing:
        # Update existing rating
        existing.rating = rating
        existing.review = review
        existing.updated_at = datetime.now()
        db.commit()
        db.refresh(existing)
        return {"message": "Rating updated", "rating": existing}
    else:
        # Create new rating
        rating_entry = Rating(
            user_id=current_user.id,
            tmdb_id=tmdb_id,
            media_type=media_type,
            rating=rating,
            review=review
        )
        db.add(rating_entry)
        db.commit()
        db.refresh(rating_entry)
        return {"message": "Rating added", "rating": rating_entry}

@router.get("/ratings")
async def get_ratings(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Get user's ratings."""
    ratings = db.query(Rating).filter(
        Rating.user_id == current_user.id
    ).order_by(Rating.created_at.desc()).all()
    
    # Group by media type
    movies = []
    tv_shows = []
    for rating in ratings:
        if rating.media_type == "movie":
            movies.append(rating)
        else:
            tv_shows.append(rating)
    
    return {
        "movies": movies,
        "tv_shows": tv_shows,
        "total": len(ratings)
    }

@router.get("/ratings/average/{media_type}/{tmdb_id}")
async def get_average_rating(
    media_type: str,
    tmdb_id: int,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Get average rating for a movie/TV show."""
    if media_type not in ("movie", "tv"):
        raise HTTPException(status_code=400, detail="media_type must be 'movie' or 'tv'")
    
    ratings = db.query(Rating).filter(
        Rating.tmdb_id == tmdb_id,
        Rating.media_type == media_type
    ).all()
    
    if not ratings:
        return {"average_rating": 0, "count": 0}
    
    avg_rating = sum(r.rating for r in ratings) / len(ratings)
    return {
        "average_rating": round(avg_rating, 1),
        "count": len(ratings)
    }