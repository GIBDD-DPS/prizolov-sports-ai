# ============================================
# Copyright (c) 2026
# Prizolov Agent OS v3.023
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
import logging

from app.db import get_db
from app.schemas import EventResponse, RecommendationResponse, MatchStateResponse
from app.services import get_events, get_recommendations, get_match_state

logger = logging.getLogger(__name__)

router = APIRouter(tags=["sports"])

@router.get("/events", response_model=List[EventResponse])
async def list_events(
    limit: int = Query(20, ge=1, le=100),
    sport: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Получить список спортивных событий."""
    try:
        events = await get_events(db, limit=limit, sport=sport)
        return events
    except ConnectionRefusedError as e:
        logger.error(f"Ошибка подключения к БД: {e}")
        raise HTTPException(status_code=503, detail="Сервис базы данных недоступен")
    except Exception as e:
        logger.exception("Неизвестная ошибка при получении событий")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

@router.get("/recommendations", response_model=List[RecommendationResponse])
async def get_ai_recommendations(
    event_id: Optional[int] = None,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """Получить AI-рекомендации по событиям."""
    try:
        recs = await get_recommendations(db, event_id=event_id, limit=limit)
        return recs
    except ConnectionRefusedError:
        raise HTTPException(status_code=503, detail="База данных недоступна")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Ошибка получения рекомендаций")
        raise HTTPException(status_code=500, detail="Ошибка сервера")

@router.post("/state", response_model=MatchStateResponse)
async def get_match_state_api(
    home: str = Query(..., description="Название домашней команды"),
    away: str = Query(..., description="Название гостевой команды"),
    db: AsyncSession = Depends(get_db)
):
    """Получить текущее состояние матча и прогнозы."""
    try:
        state = await get_match_state(db, home, away)
        if not state:
            raise HTTPException(status_code=404, detail="Матч не найден")
        return state
    except HTTPException:
        raise
    except ConnectionRefusedError:
        raise HTTPException(status_code=503, detail="База данных недоступна")
    except Exception as e:
        logger.exception("Ошибка получения состояния матча")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка")

@router.post("/state/sync")
async def sync_match_state(data: Dict[str, Any], db: AsyncSession = Depends(get_db)):
    """Синхронизировать состояние матча (для планировщика)."""
    try:
        # здесь можно вызвать функцию обновления из БД
        return {"status": "synced", "data": data}
    except Exception as e:
        logger.error(f"Ошибка синхронизации: {e}")
        raise HTTPException(status_code=500, detail=str(e))
