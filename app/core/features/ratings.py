# Feature ratings: team strength, Elo, xG, form, schedule fatigue.

from __future__ import annotations

from typing import Any, Dict


def team_strength_rating(elo_home: float, elo_away: float, xg_home: float, xg_away: float) -> Dict[str, float]:
    base_h = (elo_home - 1500) / 400.0 + (xg_home - 1.2) * 0.15
    base_a = (elo_away - 1500) / 400.0 + (xg_away - 1.2) * 0.15
    return {
        "home": round(max(0.0, min(1.0, 0.5 + base_h)), 3),
        "away": round(max(0.0, min(1.0, 0.5 + base_a)), 3),
    }


def form_rating(event: Dict[str, Any]) -> Dict[str, float]:
    fh = float(event.get("form_home_5") or event.get("form_rating_home") or 0.5)
    fa = float(event.get("form_away_5") or event.get("form_rating_away") or 0.5)
    return {"home": round(fh, 3), "away": round(fa, 3)}


def schedule_fatigue_rating(event: Dict[str, Any]) -> Dict[str, float]:
    rest_h = float(event.get("rest_days_home") or 4)
    rest_a = float(event.get("rest_days_away") or 4)
    cong_h = float(event.get("matches_last_14d_home") or 2)
    cong_a = float(event.get("matches_last_14d_away") or 2)
    score_h = max(0.0, min(1.0, 0.5 + (rest_h - 3) * 0.05 - cong_h * 0.04))
    score_a = max(0.0, min(1.0, 0.5 + (rest_a - 3) * 0.05 - cong_a * 0.04))
    return {"home": round(score_h, 3), "away": round(score_a, 3)}
