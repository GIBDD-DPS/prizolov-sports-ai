# ============================================
# Prizolov Sports AI - Setup
# Version: 4.01 (Social Sentiment & Global AI Upgrade)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at prizolov.ru
# ============================================

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
import structlog

from app.database import get_db
from app.models import Prediction
from app.api.schemas import PredictionResponse

log = structlog.get_logger()
router = APIRouter()

@router.get("/predictions", response_model=List[PredictionResponse])
async def get_predictions(
    sport: Optional[str] = Query(None, description="Фильтр по виду спорта (football, hockey, basketball)"),
    status: Optional[str] = Query("upcoming", description="Фильтр по статусу (upcoming, live, finished)"),
    confidence: Optional[str] = Query(None, description="Фильтр по уверенности (High, Med, Low)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """Получение списка прогнозов с фильтрацией для вывода на сайт"""
    query = select(Prediction)
    if sport:
        query = query.where(Prediction.sport_type == sport)
    if status:
        query = query.where(Prediction.status == status)
    if confidence:
        query = query.where(Prediction.confidence == confidence)

    query = query.order_by(Prediction.start_time.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/predictions/{match_id}", response_model=PredictionResponse)
async def get_prediction_by_id(match_id: str, db: AsyncSession = Depends(get_db)):
    """Детальный прогноз по ID матча"""
    result = await db.execute(select(Prediction).where(Prediction.match_id == match_id))
    pred = result.scalars().first()
    if not pred:
        raise HTTPException(status_code=404, detail="Prediction not found")
    return pred

@router.get("/stats/dashboard")
async def get_prediction_stats(db: AsyncSession = Depends(get_db)):
    """Краткая сводка для дашборда фронтенда"""
    total_q = select(func.count()).select_from(Prediction)
    high_q = select(func.count()).select_from(Prediction).where(Prediction.confidence == "High")
    
    total_res = await db.execute(total_q)
    high_res = await db.execute(high_q)
    
    return {
        "total_predictions": total_res.scalar_one(),
        "high_confidence_count": high_res.scalar_one(),
        "version": "4.01",
        "timestamp": "now"
    }
