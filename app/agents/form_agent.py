from __future__ import annotations

from typing import Any, Dict

from agents.base import BaseAgent
from core.features.ratings import form_rating
from prediction.calendar_strength import assess_calendar


class FormAgent(BaseAgent):
    agent_id = "form"
    name = "Form Agent"

    def run(self, event: Dict[str, Any], *, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        cal = assess_calendar(event)
        fr = form_rating(event)
        return {
            "last_5_home": event.get("last_5_home"),
            "last_5_away": event.get("last_5_away"),
            "last_10_home": event.get("last_10_home"),
            "last_10_away": event.get("last_10_away"),
            "home_form_rating": fr["home"],
            "away_form_rating": fr["away"],
            "calendar": cal,
        }
