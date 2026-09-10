# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.18 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""Manual parser trigger + accuracy summary (optional API_SECRET protection)."""

from fastapi import APIRouter, Header, HTTPException, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.accuracy_log import AccuracyLog
from app.parser.runner import run_all

router = APIRouter(prefix="/admin", tags=["admin"])


def _check_secret(x_api_secret: str | None) -> None:
    if settings.api_secret and x_api_secret != settings.api_secret:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.post("/parse")
async def trigger_parse(x_api_secret: str | None = Header(default=None)) -> dict:
    _check_secret(x_api_secret)
    results = await run_all()
    return {"status": "ok", "results": results}


@router.get("/accuracy")
def get_accuracy(
    x_api_secret: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> dict:
    """Сводка по сверенным прогнозам: средний Brier score и hit rate."""
    _check_secret(x_api_secret)

    total = db.query(func.count(AccuracyLog.id)).scalar() or 0
    if total == 0:
        return {
            "reconciled_predictions": 0,
            "avg_brier_score": None,
            "hit_rate": None,
            "note": "Пока нет ни одного сверенного матча — либо ещё не прошло "
            "FINALIZE_DELAY после kickoff, либо парсер ещё не запускался "
            "после появления этой функции.",
        }

    avg_brier = db.query(func.avg(AccuracyLog.brier_score)).scalar()
    correct_count = (
        db.query(func.count(AccuracyLog.id)).filter(AccuracyLog.correct.is_(True)).scalar()
    )

    return {
        "reconciled_predictions": total,
        "avg_brier_score": round(float(avg_brier), 4) if avg_brier is not None else None,
        "hit_rate": round(correct_count / total, 4),
        "correct": correct_count,
        "incorrect": total - correct_count,
    }
