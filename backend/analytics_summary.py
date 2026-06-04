"""Analytics summary endpoint."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/summary")
async def analytics_summary(
    days: int = Query(7, ge=1, le=90),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Get analytics summary."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Calculate date range
    from datetime import datetime, timedelta, timezone
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=days)
    
    # Get events by type
    events = db.query(
        AnalyticsEvent.event_type,
        func.count().label("count")
    ).filter(
        AnalyticsEvent.created_at.between(start_time, end_time)
    ).group_by(AnalyticsEvent.event_type).all()
    
    # Get top events by type
    top_events = {}
    for event_type in ["play", "pause", "stop", "error", "click"]:
        events_of_type = db.query(AnalyticsEvent).filter(
            AnalyticsEvent.event_type == event_type,
            AnalyticsEvent.created_at.between(start_time, end_time)
        ).order_by(AnalyticsEvent.created_at.desc()).limit(10).all()
        top_events[event_type] = events_of_type
    
    return {
        "summary": {
            "period": days,
            "total_events": sum(count for _, count in events),
            "events_by_type": dict(events),
            "top_events": top_events,
        }
    }