# ============================================
# Copyright (c) 2026
# Prizolov Agent OS v3.023
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime

# Импорт сборщиков данных
from data_ingest.free_apis import fetch_free_apis
from data_ingest.aggregators import fetch_aggregators
from data_ingest.telegram_parser import parse_telegram
from data_ingest.bookmakers import fetch_bookmakers

# Импорт обработчиков для AI и ML (опционально)
from app.core.ml_layer import MLLayer
from app.core.ai_sentiment_layer import AISentimentLayer

logger = logging.getLogger(__name__)

# Создание планировщика
scheduler = AsyncIOScheduler()

async def run_pipeline(source_type: str = "all"):
    """
    Запуск основного пайплайна обработки данных.
    source_type: 'live', 'historical', 'all'
    """
    logger.info(f"Запуск пайплайна: {source_type}")
    # Здесь можно вызвать обновление ML-моделей, пересчёт прогнозов и т.д.
    return {"status": "started", "source": source_type}

async def _run_collection_cycle():
    """Выполняет один цикл сбора данных от всех источников с обработкой ошибок."""
    tasks = [
        fetch_free_apis(),
        fetch_aggregators(),
        parse_telegram(),
        fetch_bookmakers()
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    success_count = 0
    error_count = 0
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            error_count += 1
            logger.error(f"Ошибка в сборщике {i}: {type(result).__name__}: {result}")
        else:
            success_count += 1
            logger.info(f"Сборщик {i} завершён, получено записей: {len(result) if hasattr(result, '__len__') else '?'}")
    logger.info(f"Цикл сбора завершён. Успешно: {success_count}, Ошибок: {error_count}")
    return {"success": success_count, "errors": error_count}

def start_scheduler():
    """Запускает фоновый планировщик с периодическим сбором данных."""
    # Сбор данных каждые 60 секунд
    scheduler.add_job(
        _run_collection_cycle,
        trigger=IntervalTrigger(seconds=60),
        id="collection_cycle",
        replace_existing=True,
        coalesce=True,           # не накапливать пропущенные запуски
        max_instances=1          # не запускать параллельно
    )
    # Ежечасный пайплайн для тяжёлых расчётов (опционально)
    scheduler.add_job(
        lambda: asyncio.create_task(run_pipeline("live")),
        trigger=CronTrigger(minute=0),
        id="pipeline_hourly",
        replace_existing=True
    )
    scheduler.start()
    logger.info("Планировщик запущен: сбор данных каждые 60 секунд, пайплайн каждый час")

def stop_scheduler():
    """Останавливает планировщик."""
    scheduler.shutdown(wait=False)
    logger.info("Планировщик остановлен")
