# Fixture calendar strength: opponent level, rest, travel, congestion.

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional


def _parse_start(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def assess_calendar(
    event: Dict[str, Any],
    *,
    opponent_strength_home: float = 0.5,
    opponent_strength_away: float = 0.5,
    rest_days_home: Optional[float] = None,
    rest_days_away: Optional[float] = None,
    travel_km_home: float = 0.0,
    travel_km_away: float = 0.0,
    matches_last_14d_home: int = 2,
    matches_last_14d_away: int = 2,
) -> Dict[str, Any]:
    rest_h = rest_days_home if rest_days_home is not None else float(event.get("rest_days_home") or 4)
    rest_a = rest_days_away if rest_days_away is not None else float(event.get("rest_days_away") or 4)
    fatigue_h = min(1.0, matches_last_14d_home / 5.0)
    fatigue_a = min(1.0, matches_last_14d_away / 5.0)
    travel_pen_h = min(0.12, travel_km_home / 5000.0)
    travel_pen_a = min(0.12, travel_km_away / 5000.0)

    home_edge = (opponent_strength_away - opponent_strength_home) * 0.08
    home_edge += min(0.08, (rest_h - rest_a) * 0.02)
    home_edge -= fatigue_h * 0.05 + travel_pen_h
    away_edge = -home_edge - fatigue_a * 0.03 - travel_pen_a

    return {
        "home_calendar_score": round(0.5 + home_edge, 3),
        "away_calendar_score": round(0.5 + away_edge, 3),
        "rest_days_home": rest_h,
        "rest_days_away": rest_a,
        "fatigue_home": round(fatigue_h, 3),
        "fatigue_away": round(fatigue_a, 3),
        "congestion_home": matches_last_14d_home,
        "congestion_away": matches_last_14d_away,
    }


def calendar_to_1x2(calendar: Dict[str, Any]) -> Dict[str, float]:
    h = float(calendar.get("home_calendar_score") or 0.5)
    a = float(calendar.get("away_calendar_score") or 0.5)
    draw = 0.24
    scale = 1.0 - draw
    total = h + a or 1.0
    return {
        "home_win": round(scale * h / total, 4),
        "draw": draw,
        "away_win": round(scale * a / total, 4),
    }
