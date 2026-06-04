# Tournament motivation: title race, europe, relegation.

from __future__ import annotations

from typing import Any, Dict


def motivation_context(event: Dict[str, Any], ctx: Dict[str, Any] | None = None) -> Dict[str, Any]:
    data = ctx or event.get("motivation") or {}
    home_tags = list(data.get("home_tags") or [])
    away_tags = list(data.get("away_tags") or [])
    score_h = 0.5
    score_a = 0.5
    for tag in home_tags:
        if tag in {"title_race", "ucl", "uel", "relegation_fight"}:
            score_h += 0.06
        if tag in {"nothing_to_play"}:
            score_h -= 0.08
    for tag in away_tags:
        if tag in {"title_race", "ucl", "uel", "relegation_fight"}:
            score_a += 0.06
        if tag in {"nothing_to_play"}:
            score_a -= 0.08
    return {
        "home_motivation": round(min(0.95, max(0.2, score_h)), 3),
        "away_motivation": round(min(0.95, max(0.2, score_a)), 3),
        "home_tags": home_tags,
        "away_tags": away_tags,
    }


def motivation_to_1x2(mot: Dict[str, Any]) -> Dict[str, float]:
    h = float(mot.get("home_motivation") or 0.5)
    a = float(mot.get("away_motivation") or 0.5)
    d = 0.22
    s = 1.0 - d
    t = h + a or 1.0
    return {"home_win": round(s * h / t, 4), "draw": d, "away_win": round(s * a / t, 4)}
