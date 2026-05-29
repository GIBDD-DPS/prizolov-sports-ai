# ============================================
# Copyright (c) 2026
# Prizolov Agent OS v3.023
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis
import os

from app.api.router import router as api_router
from app.db import engine, get_db, init_db
from app.scheduler import start_scheduler, stop_scheduler
from app.core.ml_layer import MLLayer
from app.core.ai_sentiment_layer import AISentimentLayer

logger = logging.getLogger(__name__)

# Глобальные экземпляры ML и AI (с fallback)
ml_layer = MLLayer(model_path=os.getenv("ML_MODEL_PATH"))
ai_sentiment = AISentimentLayer(model_name=os.getenv("SENTIMENT_MODEL_NAME"))

# Redis клиент (если используется)
redis_client = redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    decode_responses=True
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения."""
    # Startup
    logger.info("Запуск приложения Prizolov Sports AI")
    await init_db()
    start_scheduler()
    yield
    # Shutdown
    stop_scheduler()
    await engine.dispose()
    await redis_client.close()
    logger.info("Приложение остановлено")

app = FastAPI(
    title="Prizolov Sports AI",
    description="Анализ спортивных событий с AI и ML",
    version="3.023",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Для продакшена указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение маршрутов API
app.include_router(api_router, prefix="/api/v1")

# ========== Эндпоинты ==========
@app.get("/")
async def root():
    return {"message": "Prizolov Sports AI API", "version": "3.023"}

@app.get("/health")
async def health_check():
    """Проверка работоспособности сервиса (лёгкая)."""
    return {"status": "ok"}

@app.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Проверка готовности сервиса (включая БД и Redis)."""
    errors = []
    # Проверка БД
    try:
        await db.execute("SELECT 1")
    except Exception as e:
        errors.append(f"Database error: {e}")
    # Проверка Redis
    try:
        await redis_client.ping()
    except Exception as e:
        errors.append(f"Redis error: {e}")
    if errors:
        raise HTTPException(status_code=503, detail={"status": "not ready", "errors": errors})
    return {"status": "ready", "database": "connected", "redis": "connected"}

@app.get("/ml/predict")
async def predict(features: dict):
    """Эндпоинт для ML-предсказаний с fallback."""
    result = ml_layer.predict(features)
    return result

@app.post("/sentiment/analyze")
async def analyze_sentiment(text: str):
    """Анализ тональности текста с fallback."""
    result = ai_sentiment.analyze(text)
    return result

# Дополнительные эндпоинты (примеры)
@app.get("/config")
async def get_config():
    """Возвращает публичную конфигурацию (без секретов)."""
    return {
        "app_name": "Prizolov Sports AI",
        "version": "3.023",
        "ml_available": ml_layer.model is not None,
        "nlp_available": ai_sentiment.sentiment_pipeline is not None
    }
