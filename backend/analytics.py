"""Analytics tracking for watchfy backend."""
from __future__ import annotations

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .database import get_db, AnalyticsEvent
from .auth import get_current_active_user

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.post("/track")
async def track_event(
    event_type: str,
    data: Dict[str, Any] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    """Track an analytics event."""
    event = AnalyticsEvent(
        user_id=current_user.id,
        event_type=event_type,
        event_data=data or {}
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    
    return {"message": "Event tracked", "event_id": event.id}

@router.get("/events")
async def get_events(
    event_type: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Get analytics events (admin only)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    events = db.query(AnalyticsEvent).filter(
        AnalyticsEvent.user_id == current_user.id
    ).order_by(AnalyticsEvent.created_at.desc()).limit(limit).all()
    
    return {
        "events": [
            {
                "id": e.id,
                "event_type": e.event_type,
                "data": e.event_data,
                "created_at": e.created_at.isoformat(),
                "user_id": e.user_id
            }
            for e in events
        ]
    }