# backend/app/main.py
# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.40 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import admin, events, health, predictions, sports
from app.core.config import settings
from app.core.copyright import AUTHOR, ORGANIZATION, PRODUCT_NAME, PRODUCT_VERSION
from app.services.parser_scheduler import start_parser_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("prizolov.startup")

STARTUP_BANNER = f"""
================================================================
  {PRODUCT_NAME} v{PRODUCT_VERSION} (STORE-FRONT OPTIMIZED)
  Author: {AUTHOR} | {ORGANIZATION}
  Amvera app: {settings.amvera_app_name}
  Health: {settings.api_prefix}/health
  Sources: forebet.com | predictz.com | ru.betensured.com
  NOT pari.ru - if you see pari.ru in logs, WRONG build deployed
================================================================
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(STARTUP_BANNER)
    logger.info("Database host: %s", settings.postgres_host)
    logger.info(
        "Parser enabled: %s (every %s min)",
        settings.parser_enabled,
        settings.parser_interval_minutes,
    )
    scheduler_task = start_parser_scheduler()
    yield
    if scheduler_task and not scheduler_task.done():
        scheduler_task.cancel()


app = FastAPI(
    title=PRODUCT_NAME,
    version=PRODUCT_VERSION,
    description=(
        f"Public sports prediction platform. Author: {AUTHOR}. "
        f"Organization: {ORGANIZATION}."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

api_prefix = settings.api_prefix
app.include_router(health.router, prefix=api_prefix)
app.include_router(sports.router, prefix=api_prefix)
app.include_router(events.router, prefix=api_prefix)
app.include_router(predictions.router, prefix=api_prefix)
app.include_router(admin.router, prefix=api_prefix)


@app.get(f"{api_prefix}/storefront-widget")
async def storefront_widget():
    return {"status": "ok", "message": "Виджет работает"}

static_dir = Path(__file__).resolve().parent.parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
