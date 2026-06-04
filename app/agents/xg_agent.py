from __future__ import annotations

from typing import Any, Dict

from agents.base import BaseAgent
from prediction.xg_football import build_football_xg_profile


class XGAgent(BaseAgent):
    agent_id = "xg"
    name = "xG Agent"

    def run(self, event: Dict[str, Any], *, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        profile = build_football_xg_profile(event, event.get("xg_stats"))
        off_h = float(profile.get("xg_home") or 1.2)
        def_h = float(profile.get("xga_home") or 1.2)
        off_a = float(profile.get("xg_away") or 1.1)
        def_a = float(profile.get("xga_away") or 1.1)
        return {
            "profile": profile,
            "offensive_rating": {"home": round(off_h, 3), "away": round(off_a, 3)},
            "defensive_rating": {"home": round(def_h, 3), "away": round(def_a, 3)},
        }
