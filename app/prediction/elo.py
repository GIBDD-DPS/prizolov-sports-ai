# Elo ratings for teams (football-first, works for any sport key).

from __future__ import annotations

from typing import Any, Dict, Tuple

from prediction.store import get_elo, set_elo

K_FACTOR = 24.0
HOME_ADV_ELO = 65.0


def expected_score(rating_a: float, rating_b: float) -> float:
    return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))


def elo_to_1x2(home: str, away: str, *, sport: str = "football") -> Dict[str, float]:
    rh = get_elo(home) + (HOME_ADV_ELO if sport == "football" else 25.0)
    ra = get_elo(away)
    p_home = expected_score(rh, ra)
    p_away = expected_score(ra, rh)
    if sport == "football":
        draw_share = max(0.12, min(0.32, 0.26 - abs(p_home - p_away) * 0.15))
        scale = 1.0 - draw_share
        return {
            "home_win": p_home * scale,
            "draw": draw_share,
            "away_win": p_away * scale,
        }
    total = p_home + p_away
    if total <= 0:
        return {"home_win": 0.5, "draw": 0.0, "away_win": 0.5}
    return {"home_win": p_home / total, "draw": 0.0, "away_win": p_away / total}


def update_elo_after_result(
    home: str,
    away: str,
    *,
    home_goals: int,
    away_goals: int,
    sport: str = "football",
) -> Tuple[float, float]:
    rh = get_elo(home)
    ra = get_elo(away)
    if home_goals > away_goals:
        score_h, score_a = 1.0, 0.0
    elif home_goals < away_goals:
        score_h, score_a = 0.0, 1.0
    else:
        score_h, score_a = 0.5, 0.5 if sport == "football" else 0.0

    exp_h = expected_score(rh + HOME_ADV_ELO * 0.5, ra)
    new_h = rh + K_FACTOR * (score_h - exp_h)
    new_a = ra + K_FACTOR * (score_a - (1.0 - exp_h))
    set_elo(home, new_h)
    set_elo(away, new_a)
    return new_h, new_a


def elo_context(event: Dict[str, Any]) -> Dict[str, Any]:
    home = str(event.get("home") or "")
    away = str(event.get("away") or "")
    sport = str(event.get("sport") or "football")
    probs = elo_to_1x2(home, away, sport=sport)
    return {
        "home_rating": get_elo(home),
        "away_rating": get_elo(away),
        "probabilities": probs,
    }
