# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.06 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""Normalize raw parser output into unified event schema."""

from typing import Any


def normalize_event(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "sport": "football",
        "home_team": raw.get("home_team", ""),
        "away_team": raw.get("away_team", ""),
        "league": raw.get("league", ""),
        "kickoff": raw.get("kickoff"),
        "source_id": raw.get("source_id"),
        "markets": raw.get("markets", []),
    }
