# Feature engine — builds all ratings for ML / agents.

from __future__ import annotations

from typing import Any, Dict

from core.features.ratings import form_rating, schedule_fatigue_rating, team_strength_rating
from core.system_monitor.latency import track_stage


def build_features(event: Dict[str, Any]) -> Dict[str, Any]:
    with track_stage("feature_engineering"):
        from prediction.elo import elo_context
        from prediction.store import get_elo
        from prediction.xg_football import build_football_xg_profile

        elo = elo_context(event)
        xg = build_football_xg_profile(event, event.get("xg_stats"))
        home = str(event.get("home") or "")
        away = str(event.get("away") or "")

        ratings = {
            "elo_rating": {
                "home": elo.get("home_rating", get_elo(home)),
                "away": elo.get("away_rating", get_elo(away)),
            },
            "xg_rating": {
                "offensive_home": float(xg.get("xg_home") or 1.3),
                "defensive_home": float(xg.get("xga_home") or 1.2),
                "offensive_away": float(xg.get("xg_away") or 1.1),
                "defensive_away": float(xg.get("xga_away") or 1.3),
            },
            "form_rating": form_rating(event),
            "schedule_fatigue_rating": schedule_fatigue_rating(event),
            "team_strength_rating": team_strength_rating(
                float(elo.get("home_rating") or 1500),
                float(elo.get("away_rating") or 1500),
                float(xg.get("xg_home") or 1.3),
                float(xg.get("xg_away") or 1.1),
            ),
        }
        return {"event_key": f"{home}|{away}|{event.get('sport')}", "ratings": ratings, "raw_xg": xg}
