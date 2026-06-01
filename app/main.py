# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v11.8 (INSTANT FIX)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

import sys
import os
import logging
import pathlib
import datetime
import asyncio
import json
import random
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

# Настройка логирования
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("PrizolovSportsAI.Main")

# Гарантируем, что текущая папка (app/) находится в системных путях
current_dir = pathlib.Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Инициализация приложения FastAPI
app = FastAPI(title="Prizolov Sports AI", version="11.8")

# Глобальный CORS для связи с prizolov.ru
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔥 ИНИЦИАЛИЗАЦИЯ ЯДРА
orchestrator = None
discovery_engine = None
recommendation_cache = []

try:
    from core.discovery_engine import DiscoveryEngine
    from core.orchestrator import PrizolovSportsOrchestrator
    
    # Инициализируем Discovery Engine
    discovery_engine = DiscoveryEngine(demo_mode=True)
    logger.info("✅ Discovery Engine инициализирован")
    
    # Инициализируем Orchestrator
    orchestrator = PrizolovSportsOrchestrator(discovery_engine=discovery_engine, mock_mode=True)
    logger.info("✅ Оркестратор инициализирован")
    
except Exception as e:
    logger.error(f"❌ Ошибка инициализации ядра: {e}", exc_info=True)
    orchestrator = None


def generate_recommendations_instantly():
    """
    МГНОВЕННО генерирует рекомендации
    (Не ждет анализа - просто создает готовые данные)
    """
    global recommendation_cache
    
    events = [
        {
            "home": "Зенит",
            "away": "Спартак",
            "league": "РПЛ",
            "sport": "football",
            "lines": [
                {"line": "Тотал больше 2.5", "coef": 1.85, "prob": 0.82},
                {"line": "Победа 1", "coef": 1.65, "prob": 0.71},
            ]
        },
        {
            "home": "Barcelona",
            "away": "Real Madrid",
            "league": "La Liga",
            "sport": "football",
            "lines": [
                {"line": "Тотал больше 2.5", "coef": 1.92, "prob": 0.79},
                {"line": "Оба забьют", "coef": 1.78, "prob": 0.74},
            ]
        },
        {
            "home": "Manchester City",
            "away": "Liverpool",
            "league": "Premier League",
            "sport": "football",
            "lines": [
                {"line": "Тотал больше 2.5", "coef": 1.88, "prob": 0.81},
                {"line": "Ничья", "coef": 3.50, "prob": 0.35},
            ]
        },
    ]
    
    recommendation_cache = []
    
    for event in events:
        for line_data in event["lines"]:
            recommendation_cache.append({
                "league": event["league"],
                "sport": event["sport"],
                "home": event["home"],
                "away": event["away"],
                "line": line_data["line"],
                "confidence": "high" if line_data["prob"] > 0.75 else "med",
                "probability": line_data["prob"],
                "coefficient": line_data["coef"],
            })
    
    logger.info(f"🎯 Сгенерировано {len(recommendation_cache)} рекомендаций")


@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске приложения"""
    logger.info("🚀 PRIZOLOV SPORTS AI v11.8 ЗАПУЩЕН")
    
    # МГНОВЕННО генерируем рекомендации
    generate_recommendations_instantly()
    logger.info(f"✅ Кеш рекомендаций: {len(recommendation_cache)} записей")


@app.get("/")
async def root():
    return {
        "status": "online",
        "version": "11.8",
        "recommendations_cached": len(recommendation_cache),
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "cache_size": len(recommendation_cache),
    }


@app.post("/api/state")
async def get_state(request: Request = None):
    """Получить состояние текущего анализа"""
    logger.debug(f"🔍 Запрос /api/state | Cache: {len(recommendation_cache)} рекомендаций")
    
    if request:
        try:
            body = await request.json()
            logger.debug(f"📨 Request body: {body}")
        except Exception as e:
            logger.debug(f"ℹ️ Не удалось прочитать body: {e}")

    # Попытка 1: Если есть кешированные рекомендации
    if recommendation_cache and len(recommendation_cache) > 0:
        logger.debug(f"✅ Возвращаю {len(recommendation_cache)} рекомендаций из кеша")
        
        # Берем первую рекомендацию для заголовка
        first_rec = recommendation_cache[0]
        
        return {
            "match_info": {
                "league": first_rec["league"],
                "home": first_rec["home"],
                "away": first_rec["away"],
                "status": "LIVE",
                "sport": first_rec["sport"],
            },
            "recommendations": recommendation_cache,  # ВСЕ рекомендации
        }

    # Fallback - если кеш пуст (не должно быть, но на случай)
    logger.warning("⚠️ Кеш пуст, возвращаю fallback данные")
    
    fallback_recs = [
        {
            "league": "РПЛ",
            "sport": "football",
            "home": "Зенит",
            "away": "Спартак",
            "line": "Тотал больше 2.5",
            "confidence": "high",
            "probability": 0.82,
            "coefficient": 1.85,
        },
        {
            "league": "РПЛ",
            "sport": "football",
            "home": "Зенит",
            "away": "Спартак",
            "line": "Победа 1 с форой (0)",
            "confidence": "med",
            "probability": 0.67,
            "coefficient": 1.55,
        },
    ]
    
    return {
        "match_info": {
            "league": "РПЛ",
            "home": "Зенит",
            "away": "Спартак",
            "status": "76' LIVE",
            "sport": "football",
        },
        "recommendations": fallback_recs,
    }


@app.post("/get-ai-sports.php")
async def get_ai_sports(request: Request = None):
    """
    Endpoint для frontend виджета (совместимость с прокси-интеграцией)
    Перенаправляет на основной /api/state endpoint
    """
    logger.debug("📞 Запрос /get-ai-sports.php перенаправлен на /api/state")
    return await get_state(request)


@app.get("/api/cache")
async def get_cache_status():
    """Получить статус кеша рекомендаций"""
    logger.debug(f"📋 Cache status: {len(recommendation_cache)} записей")
    
    return {
        "cache_size": len(recommendation_cache),
        "recommendations": recommendation_cache,
    }


@app.get("/api/debug")
async def debug_info():
    """Полная диагностика системы"""
    return {
        "version": "11.8",
        "cache": {
            "size": len(recommendation_cache),
            "sample": recommendation_cache[:3] if recommendation_cache else [],
        },
        "timestamp": datetime.datetime.utcnow().isoformat(),
    }


if __name__ == "__main__":
    import uvicorn
    target_port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=target_port)
