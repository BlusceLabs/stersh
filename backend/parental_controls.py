"""Parental controls router for watchfy backend."""
from __future__ import annotations

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .database import get_db, User
from .auth import get_current_active_user

router = APIRouter(prefix="/parental", tags=["parental"])

@router.get("/settings")
async def get_parental_settings(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Get parental control settings for user."""
    # For now, return default settings
    # In a real app, this would store settings in the database
    return {
        "allowed_genres": [],  # All genres allowed by default
        "blocked_genres": [],  # No genres blocked by default
        "max_rating": "R",  # G, PG, PG-13, R, NC-17, TV-Y, TV-Y7, TV-G, TV-PG, TV-14, TV-MA
        "enabled": False,
        "pin": None  # Hashed PIN if set
    }

@router.post("/settings")
async def update_parental_settings(
    settings: Dict[str, Any],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Update parental control settings."""
    # In a real app, this would update the database
    # For now, just return the settings
    return {
        "message": "Parental settings updated",
        "settings": settings
    }

@router.post("/validate/{media_type}/{tmdb_id}")
async def validate_content(
    media_type: str,
    tmdb_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Check if content is allowed based on parental controls."""
    # For now, always return allowed
    # In a real app, this would check:
    # - Content rating against max_rating
    # - Genre blocking
    # - PIN protection
    return {
        "allowed": True,
        "reasons": []  # Reasons if not allowed (e.g., "R rating", "Blocked genre")
    }