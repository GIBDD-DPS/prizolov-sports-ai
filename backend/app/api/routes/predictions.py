# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.40 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""Predictions endpoint."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models.event import Event
from app.models.prediction import Prediction
from app.models.sport import Sport
from app.schemas.api import PredictionOut

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.get("")
def list_predictions(
    sport: str = Query(default="football"),
    event_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> dict:
    sport_row = db.query(Sport).filter(Sport.slug == sport).first()
    if not sport_row:
        raise HTTPException(status_code=404, detail=f"Sport '{sport}' not found")

    query = (
        db.query(Prediction)
        .join(Event, Prediction.event_id == Event.id)
        .options(joinedload(Prediction.market))
        .filter(Event.sport_id == sport_row.id)
        .order_by(Prediction.created_at.desc())
    )

    if event_id is not None:
        query = query.filter(Prediction.event_id == event_id)

    rows = query.limit(limit).all()

    items = [
        PredictionOut(
            id=p.id,
            event_id=p.event_id,
            market_type=p.market.market_type,
            line_value=p.market.line_value,
            selection=p.selection,
            probability=p.probability,
            confidence=p.confidence,
            factors=p.factors,
        )
        for p in rows
    ]
    return {
        "sport": sport,
        "event_id": event_id,
        "count": len(items),
        "items": items,
    }
