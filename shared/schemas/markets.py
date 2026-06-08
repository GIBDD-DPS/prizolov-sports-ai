# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.14 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""Shared market type definitions."""

from enum import Enum


class MarketType(str, Enum):
    ONE_X_TWO = "1X2"
    TOTAL_GOALS = "TOTAL_GOALS"
    YELLOW_CARDS = "YELLOW_CARDS"
    CORNERS = "CORNERS"


MARKET_LABELS = {
    MarketType.ONE_X_TWO: "П1 / X / П2",
    MarketType.TOTAL_GOALS: "Тотал голов",
    MarketType.YELLOW_CARDS: "ЖК",
    MarketType.CORNERS: "Угловые",
}
