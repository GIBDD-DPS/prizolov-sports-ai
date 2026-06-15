# backend/app/main.py
# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.24 (STORE-FRONT)
# Author: Dm.Andreyanov
# ============================================

import logging
from fastapi import FastAPI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("prizolov.api")

app = FastAPI(title="Prizolov Sports AI Storefront")

@app.get("/api/v1/storefront-widget")
async def storefront_widget():
    return {"status": "ok", "message": "Виджет работает"}

@app.get("/health")
async def health():
    return {"status": "ok"}
