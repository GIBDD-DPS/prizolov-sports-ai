from __future__ import annotations

from typing import Any, Dict

from prediction.xg_football import build_football_xg_profile, xg_to_1x2


def run(event: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, float]:
    profile = context.get("xg_profile") or build_football_xg_profile(event)
    if str(event.get("sport") or "") == "football":
        return xg_to_1x2(profile)
    xg = profile
    h = float(xg.get("xg_home") or 1.2)
    a = float(xg.get("xg_away") or 1.0)
    t = h + a or 1.0
    return {"home_win": h / t * 0.75, "draw": 0.25, "away_win": a / t * 0.75}
