# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.40 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""Sports listing endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.sport import Sport
from app.schemas.api import SportOut

router = APIRouter(prefix="/sports", tags=["sports"])


@router.get("")
def list_sports(db: Session = Depends(get_db)) -> list[SportOut]:
    sports = db.query(Sport).order_by(Sport.id).all()
    return [SportOut.model_validate(s) for s in sports]
