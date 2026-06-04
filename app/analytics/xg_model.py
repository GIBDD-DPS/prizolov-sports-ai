# Expected goals (xG) / expected goals against (xGA) for match context.

from __future__ import annotations

import math
from typing import Any, Dict, Optional

from analytics.store import set_xg_cache


def _parse_score(score: str) -> tuple[Optional[int], Optional[int]]:
    if not score or score == "—":
        return None, None
    parts = str(score).replace(" ", "").split(":")
    if len(parts) != 2:
        return None, None
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None, None


def estimate_xg_xga(
    event: Dict[str, Any],
    *,
    home_form: Optional[float] = None,
    away_form: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Lightweight xG/xGA model for storefront events.
    Uses score + sport priors; extend later with shot data / Understat API.
    """
    sport = str(event.get("sport") or "football").lower()
    home = event.get("home") or "Home"
    away = event.get("away") or "Away"

    if sport == "hockey":
        base_home, base_away = 2.8, 2.6
    elif sport == "basketball":
        base_home, base_away = 110.0, 108.0
    else:
        base_home, base_away = 1.35, 1.15

    home_goals, away_goals = _parse_score(str(event.get("score") or ""))
    minute_raw = str(event.get("live_minute") or "").replace("'", "").strip()
    try:
        elapsed = max(1, int("".join(ch for ch in minute_raw if ch.isdigit()) or "0"))
    except ValueError:
        elapsed = 45 if event.get("is_live") else 90

    if event.get("is_live") and home_goals is not None and away_goals is not None:
        pace = 90.0 / min(elapsed, 90)
        xg_home = max(0.05, (home_goals + 0.25) * pace * 0.92)
        xg_away = max(0.05, (away_goals + 0.25) * pace * 0.92)
    else:
        xg_home = base_home * (home_form or 1.0)
        xg_away = base_away * (away_form or 1.0)

    if sport == "football":
        xg_home *= 1.08  # home advantage
        xga_home = xg_away
        xga_away = xg_home
    else:
        xga_home = xg_away
        xga_away = xg_home

    total_xg = xg_home + xg_away
    payload = {
        "sport": sport,
        "home": home,
        "away": away,
        "xg_home": round(xg_home, 3),
        "xg_away": round(xg_away, 3),
        "xga_home": round(xga_home, 3),
        "xga_away": round(xga_away, 3),
        "total_xg": round(total_xg, 3),
        "model": "prizolov_xg_v1",
        "is_live": bool(event.get("is_live")),
    }
    return payload


def enrich_event_with_xg(event: Dict[str, Any]) -> Dict[str, Any]:
    key = f"{event.get('home')}|{event.get('away')}|{event.get('sport')}"
    metrics = estimate_xg_xga(event)
    set_xg_cache(key, metrics)
    event = dict(event)
    event["xg_metrics"] = metrics
    return event
