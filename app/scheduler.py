# ============================================
# Prizolov Sports AI - Setup
# Version: 4.01 (Social Sentiment & Global AI Upgrade)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at prizolov.ru
# ============================================

import asyncio
import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from typing import List, Dict, Any
from datetime import datetime

from app.config import settings
from app.database import AsyncSession
from app.models import Prediction
from app.core.prediction_engine import generate_prediction

# Импорт коллекторов
from data_ingest.free_apis import FreeAPICollector
from data_ingest.aggregators import AggregatorCollector
from data_ingest.telegram_parser import TelegramCollector
from data_ingest.bookmakers import BookmakerCollector

log = structlog.get_logger()
scheduler = AsyncIOScheduler()

async def _run_collection_cycle(pipeline_type: str) -> List[Dict]:
    """Инициализация и запуск всех сборщиков в зависимости от типа пайплайна"""
    api_keys = {"the-odds": settings.API_KEYS_ODDS, "api-sports": settings.API_KEYS_SPORTS}
    tg_cfg = {
        "api_id": int(settings.TELEGRAM_API_ID or 0),
        "api_hash": settings.TELEGRAM_API_HASH or "",
        "session_string": settings.TELEGRAM_SESSION
    }
    channels = (settings.TELEGRAM_CHANNELS or "").split(",") if getattr(settings, "TELEGRAM_CHANNELS", None) else []
    ua = "PrizolovSportsAI/4.01"

    raw_events = []
    try:
        async with FreeAPICollector(api_keys) as api_col, \
                   AggregatorCollector(user_agent=ua) as agg_col, \
                   TelegramCollector(**tg_cfg) as tg_col, \
                   BookmakerCollector(user_agent=ua) as bk_col:
            
            tasks = []
            if pipeline_type in ("live", "odds"):
                tasks.append(api_col.fetch_odds())
                tasks.append(bk_col.collect_all_bk())
                tasks.append(agg_col.fetch_live_matches("flashscore"))
                
                if pipeline_type == "live" and channels:
                    tasks.append(tg_col.collect_from_channels(channels))
            
            if pipeline_type == "prematch":
                tasks.append(api_col.fetch_events())
                
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, list):
                    raw_events.extend(res)
                elif isinstance(res, Exception):
                    log.error("Collector task failed", error=str(res), type=pipeline_type)
                    
    except Exception as e:
        log.error("Collection cycle failed", error=str(e), type=pipeline_type)
        
    log.info("Collection cycle finished", type=pipeline_type, items=len(raw_events))
    return raw_events

async def _process_and_save(events: List[Dict]):
    """Дедупликация, генерация прогнозов и запись в БД"""
    if not events:
        return

    # Простая дедупликация по match_id для демонстрации
    seen_ids = set()
    unique_events = []
    for ev in events:
        mid = ev.get("match_id")
        if mid and mid not in seen_ids:
            seen_ids.add(mid)
            unique_events.append(ev)

    async with AsyncSession() as db:
        for match in unique_events:
            try:
                pred_data = await generate_prediction(match)
                
                from sqlalchemy.dialects.postgresql import insert
                stmt = insert(Prediction).values(
                    match_id=match["match_id"],
                    home_team=match.get("home_team"),
                    away_team=match.get("away_team"),
                    sport_type=match.get("sport_type", "unknown"),
                    league=match.get("league_name"),
                    start_time=datetime.fromisoformat(match["start_time"]) if match.get("start_time") else None,
                    status=match.get("status", "upcoming"),
                    current_minute=match.get("current_minute"),
                    odds=match.get("odds"),
                    prediction_outcome=pred_data["prediction_outcome"],
                    probability=pred_data["probability"],
                    recommended_bet=pred_data["recommended_bet"],
                    expected_value=pred_data["expected_value"],
                    confidence=pred_data["confidence"],
                    layers_output={"stat": "base", "ml": "pending", "ai": "pending"},
                    created_at=datetime.utcnow()
                ).on_conflict_do_update(
                    constraint="predictions_match_id_key",
                    set_={
                        "status": stmt.excluded.status,
                        "current_minute": stmt.excluded.current_minute,
                        "odds": stmt.excluded.odds,
                        "probability": stmt.excluded.probability,
                        "prediction_outcome": stmt.excluded.prediction_outcome,
                        "recommended_bet": stmt.excluded.recommended_bet,
                        "expected_value": stmt.excluded.expected_value,
                        "confidence": stmt.excluded.confidence,
                        "updated_at": datetime.utcnow()
                    }
                )
                await db.execute(stmt)
            except Exception as e:
                log.error("Failed to process match", match_id=match.get("match_id"), error=str(e))
                
        await db.commit()
        log.info("Batch saved to DB", count=len(unique_events))

async def run_pipeline(pipeline_type: str):
    """Основная точка входа для APScheduler"""
    log.info(f"🔄 Starting {pipeline_type.upper()} pipeline")
    events = await _run_collection_cycle(pipeline_type)
    await _process_and_save(events)
    log.info(f"✅ {pipeline_type.upper()} pipeline completed")

async def start_scheduler():
    log.info("Initializing APScheduler with async tasks")
    
    scheduler.add_job(
        lambda: asyncio.create_task(run_pipeline("live")),
        IntervalTrigger(seconds=settings.LIVE_INTERVAL),
        id="live_pipeline", replace_existing=True, max_instances=1
    )
    scheduler.add_job(
        lambda: asyncio.create_task(run_pipeline("prematch")),
        IntervalTrigger(seconds=settings.PREMATCH_INTERVAL),
        id="prematch_pipeline", replace_existing=True, max_instances=1
    )
    scheduler.add_job(
        lambda: asyncio.create_task(run_pipeline("odds")),
        IntervalTrigger(seconds=settings.ODDS_INTERVAL),
        id="odds_pipeline", replace_existing=True, max_instances=1
    )
    scheduler.start()
    log.info("Scheduler started successfully")

async def stop_scheduler():
    scheduler.shutdown(wait=False)
    log.info("Scheduler stopped")
