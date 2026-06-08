# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.14 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""Manual parser trigger (protected by API_SECRET)."""

from fastapi import APIRouter, Header, HTTPException

from app.core.config import settings
from app.parser.runner import run_all

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/parse")
async def trigger_parse(x_api_secret: str | None = Header(default=None)) -> dict:
    if not settings.api_secret or x_api_secret != settings.api_secret:
        raise HTTPException(status_code=403, detail="Forbidden")

    results = await run_all()
    return {"status": "ok", "results": results}
