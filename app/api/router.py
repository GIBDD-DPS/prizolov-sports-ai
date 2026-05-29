# ============================================
# Copyright (c) 2026
# Prizolov Agent OS v3.023
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.schemas import EventResponse
from app.services import get_events
import logging

router = APIRouter(prefix="/api/v1")
logger = logging.getLogger(__name__)

@router.get("/events", response_model=list[EventResponse])
async def list_events(db: AsyncSession = Depends(get_db)):
    try:
        events = await get_events(db)
        return events
    except ConnectionRefusedError as e:
        logger.error(f"Ошибка подключения к БД: {e}")
        raise HTTPException(status_code=503, detail="Сервис временно недоступен")
    except Exception as e:
        logger.exception("Неизвестная ошибка при получении событий")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")
