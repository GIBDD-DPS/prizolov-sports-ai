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
from datetime import datetime

from data_ingest.free_apis import fetch_free_api_data
from data_ingest.aggregators import aggregate_data
from data_ingest.telegram_parser import parse_telegram
from data_ingest.bookmakers import fetch_bookmaker_odds
from app.core.pipeline import run_pipeline

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

async def _run_collection_cycle():
    """Запускает все сборщики данных параллельно с обработкой ошибок."""
    tasks = [
        fetch_free_api_data(),
        aggregate_data(),
        parse_telegram(),
        fetch_bookmaker_odds()
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for idx, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Ошибка в сборщике {idx}: {result}")
        else:
            logger.info(f"Сборщик {idx} завершил работу успешно")

async def scheduled_pipeline():
    """Задача для планировщика: запуск полного пайплайна."""
    logger.info("Запуск scheduled_pipeline (live)")
    try:
        await run_pipeline("live")
    except Exception as e:
        logger.exception(f"Ошибка в scheduled_pipeline: {e}")

def start_scheduler():
    """Инициализация и запуск планировщика."""
    # Сбор данных каждые 30 минут
    scheduler.add_job(
        _run_collection_cycle,
        trigger=IntervalTrigger(minutes=30),
        id="collect_data",
        replace_existing=True
    )
    # Полный пайплайн каждый час
    scheduler.add_job(
        scheduled_pipeline,
        trigger=IntervalTrigger(hours=1),
        id="run_pipeline",
        replace_existing=True
    )
    scheduler.start()
    logger.info("Планировщик запущен")

def shutdown_scheduler():
    """Остановка планировщика."""
    scheduler.shutdown(wait=False)
    logger.info("Планировщик остановлен")
