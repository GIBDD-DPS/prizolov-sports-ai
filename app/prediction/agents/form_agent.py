from __future__ import annotations

from typing import Any, Dict

from prediction.calendar_strength import assess_calendar, calendar_to_1x2
from prediction.elo import elo_to_1x2


def run(event: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, float]:
    cal = context.get("calendar") or assess_calendar(event)
    cal_probs = calendar_to_1x2(cal)
    elo_probs = elo_to_1x2(str(event.get("home") or ""), str(event.get("away") or ""), sport=str(event.get("sport") or "football"))
    return {
        "home_win": (cal_probs["home_win"] + elo_probs["home_win"]) / 2,
        "draw": (cal_probs["draw"] + elo_probs["draw"]) / 2,
        "away_win": (cal_probs["away_win"] + elo_probs["away_win"]) / 2,
    }
