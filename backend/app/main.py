# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.14 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import admin, events, health, predictions, sports
from app.core.config import settings
from app.core.copyright import AUTHOR, ORGANIZATION, PRODUCT_NAME, PRODUCT_VERSION
from app.services.parser_scheduler import start_parser_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
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
    allow_origins=[settings.public_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_prefix = settings.api_prefix
app.include_router(health.router, prefix=api_prefix)
app.include_router(sports.router, prefix=api_prefix)
app.include_router(events.router, prefix=api_prefix)
app.include_router(predictions.router, prefix=api_prefix)
app.include_router(admin.router, prefix=api_prefix)

static_dir = Path(__file__).resolve().parent.parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
