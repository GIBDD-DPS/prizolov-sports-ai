# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.02 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""Health check endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.copyright import AUTHOR, ORGANIZATION, PRODUCT_NAME, PRODUCT_VERSION
from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    db_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = f"error: {exc}"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "product": PRODUCT_NAME,
        "version": PRODUCT_VERSION,
        "author": AUTHOR,
        "organization": ORGANIZATION,
        "public_url": settings.public_url,
        "database": db_status,
        "postgres_host": settings.postgres_host if db_status == "ok" else None,
        "amvera_app": settings.amvera_app_name,
        "parser_enabled": settings.parser_enabled,
        "parser_interval_minutes": settings.parser_interval_minutes,
    }
