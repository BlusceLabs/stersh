"""Ad management router for watchfy backend."""
from __future__ import annotations

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from database import get_db, Ad, UserAdInteraction
from auth import get_current_active_user

router = APIRouter(prefix="/ads", tags=["ads"])


def _ad_to_dict(ad: Ad) -> Dict[str, Any]:
    return {c.name: getattr(ad, c.name) for c in ad.__table__.columns}


@router.get("/", response_model=None)
async def list_ads(
    ad_type: Optional[str] = Query(None, pattern="^(pre-roll|mid-roll|display|banner)$"),
    active: Optional[bool] = None,
    db: Session = Depends(get_db),
) -> Any:
    """List ads with filtering."""
    query = db.query(Ad).filter(Ad.active == True)
    if ad_type:
        query = query.filter(Ad.ad_type == ad_type)
    if active is not None:
        query = query.filter(Ad.active == active)
    ads = query.order_by(Ad.created_at.desc()).all()
    return [_ad_to_dict(a) for a in ads]

@router.post("/", response_model=None)
async def create_ad(
    ad_data: Dict[str, Any],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Any:
    """Create a new ad (admin only)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    ad = Ad(**ad_data)
    db.add(ad)
    db.commit()
    db.refresh(ad)
    return _ad_to_dict(ad)


@router.get("/{ad_id}", response_model=None)
async def get_ad(
    ad_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Any:
    """Get ad details (admin only)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    ad = db.query(Ad).filter(Ad.id == ad_id).first()
    if ad is None:
        raise HTTPException(status_code=404, detail="Ad not found")
    return _ad_to_dict(ad)


@router.put("/{ad_id}", response_model=None)
async def update_ad(
    ad_id: int,
    updates: Dict[str, Any],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Any:
    """Update an ad (admin only)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    ad = db.query(Ad).filter(Ad.id == ad_id).first()
    if ad is None:
        raise HTTPException(status_code=404, detail="Ad not found")
    for key, value in updates.items():
        if hasattr(ad, key) and key not in ("id", "created_at", "updated_at"):
            setattr(ad, key, value)
    db.commit()
    db.refresh(ad)
    return _ad_to_dict(ad)

@router.delete("/{ad_id}")
async def delete_ad(
    ad_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    """Delete an ad (admin only)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    ad = db.query(Ad).filter(Ad.id == ad_id).first()
    if ad is None:
        raise HTTPException(status_code=404, detail="Ad not found")
    
    db.delete(ad)
    db.commit()
    
    return {"message": "Ad deleted"}

@router.post("/{ad_id}/track")
async def track_ad_interaction(
    ad_id: int,
    interaction_type: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    """Track ad interaction (impression, click, skip)."""
    interaction = UserAdInteraction(
        user_id=current_user.id,
        ad_id=ad_id,
        interaction_type=interaction_type
    )
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    
    return {"message": "Interaction tracked", "interaction_id": interaction.id}