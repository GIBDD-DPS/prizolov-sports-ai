# backend/app/main.py
# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.24 (STORE-FRONT)
# Author: Dm.Andreyanov
# ============================================

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agenomics_integration import router as agenomics_router
from app.api.routes import admin, events, health, predictions, sports
from app.core.config import settings
from app.services.parser_scheduler import start_parser_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("prizolov.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = start_parser_scheduler()
    yield
    if task:
        task.cancel()


app = FastAPI(title="Prizolov Sports AI Storefront", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix=settings.api_prefix)
app.include_router(sports.router, prefix=settings.api_prefix)
app.include_router(events.router, prefix=settings.api_prefix)
app.include_router(predictions.router, prefix=settings.api_prefix)
app.include_router(admin.router, prefix=settings.api_prefix)
app.include_router(agenomics_router, prefix=f"{settings.api_prefix}/admin")


@app.get("/api/v1/storefront-widget")
async def storefront_widget():
    return {"status": "ok", "message": "Виджет работает"}


@app.get("/health")
async def bare_health():
    return {"status": "ok"}