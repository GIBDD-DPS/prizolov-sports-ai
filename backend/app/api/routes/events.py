# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.40 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""Events listing endpoint."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models.event import Event
from app.models.sport import Sport
from app.schemas.api import EventOut

router = APIRouter(prefix="/events", tags=["events"])


@router.get("")
def list_events(
    sport: str = Query(default="football"),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> dict:
    sport_row = db.query(Sport).filter(Sport.slug == sport).first()
    if not sport_row:
        raise HTTPException(status_code=404, detail=f"Sport '{sport}' not found")

    rows = (
        db.query(Event)
        .options(joinedload(Event.sport))
        .filter(Event.sport_id == sport_row.id)
        .order_by(Event.kickoff_at.asc())
        .limit(limit)
        .all()
    )

    items = [
        EventOut(
            id=e.id,
            home_team=e.home_team,
            away_team=e.away_team,
            league=e.league,
            kickoff_at=e.kickoff_at,
            status=e.status,
            sport_slug=e.sport.slug,
        )
        for e in rows
    ]
    return {"sport": sport, "limit": limit, "count": len(items), "items": items}


@router.get("/{event_id}")
def get_event(event_id: int, db: Session = Depends(get_db)) -> EventOut:
    event = (
        db.query(Event)
        .options(joinedload(Event.sport))
        .filter(Event.id == event_id)
        .first()
    )
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return EventOut(
        id=event.id,
        home_team=event.home_team,
        away_team=event.away_team,
        league=event.league,
        kickoff_at=event.kickoff_at,
        status=event.status,
        sport_slug=event.sport.slug,
    )
