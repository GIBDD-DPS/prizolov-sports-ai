from __future__ import annotations

from typing import Any, Dict

from agents.base import BaseAgent
from prediction.lineup import assess_lineup_risk


class InjuryAgent(BaseAgent):
    agent_id = "injury"
    name = "Injury & Lineup Agent"

    def run(self, event: Dict[str, Any], *, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        data = assess_lineup_risk(event)
        return {
            "lineup_confirmed": data.get("lineup_confirmed"),
            "injuries": event.get("injuries") or [],
            "suspensions": event.get("suspensions") or [],
            "rotation_risk": data.get("risk_flags") or [],
            "missing_players": data.get("missing_players_total", 0),
        }
