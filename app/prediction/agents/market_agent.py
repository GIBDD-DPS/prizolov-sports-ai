from __future__ import annotations

from typing import Any, Dict, List


def _implied(coef: float) -> float:
    return 1.0 / coef if coef >= 1.01 else 0.0


def run(event: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, float]:
    recs: List[Dict[str, Any]] = event.get("all_recommendations") or event.get("recommendations") or []
    home_p = draw_p = away_p = 0.0
    for rec in recs:
        line = str(rec.get("line") or "").lower()
        coef = float(rec.get("coefficient") or 0)
        if coef < 1.01:
            continue
        imp = _implied(coef)
        if "ничья" in line or " x " in line or line.endswith("x"):
            draw_p += imp
        elif "победа 1" in line or " п1" in line or line.startswith("1 "):
            home_p += imp
        elif "победа 2" in line or " п2" in line:
            away_p += imp
        elif "победа" in line and event.get("home", "").lower() in line.lower():
            home_p += imp
        elif "победа" in line:
            away_p += imp
        elif "1x" in line:
            home_p += imp * 0.7
            draw_p += imp * 0.3
        elif "x2" in line:
            away_p += imp * 0.7
            draw_p += imp * 0.3

    if home_p + draw_p + away_p < 0.01:
        return {"home_win": 0.40, "draw": 0.28, "away_win": 0.32}

    total = home_p + draw_p + away_p
    return {
        "home_win": home_p / total,
        "draw": draw_p / total,
        "away_win": away_p / total,
    }
