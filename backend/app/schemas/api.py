# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.14 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""Pydantic response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    name: str
    is_active: bool


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    home_team: str
    away_team: str
    league: str
    kickoff_at: datetime
    status: str
    sport_slug: str


class PredictionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: int
    market_type: str
    line_value: float | None
    selection: str
    probability: float
    confidence: str
    factors: dict | None
