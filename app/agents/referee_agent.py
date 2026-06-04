from __future__ import annotations

from typing import Any, Dict

from agents.base import BaseAgent
from prediction.referee import from_event as referee_from_event


class RefereeAgent(BaseAgent):
    agent_id = "referee"
    name = "Referee Agent"

    def run(self, event: Dict[str, Any], *, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        ref = referee_from_event(event)
        return {
            **ref,
            "markets": ["yellow_cards", "fouls", "penalties", "var"],
        }
