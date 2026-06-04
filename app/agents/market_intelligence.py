from __future__ import annotations

from typing import Any, Dict

from agents.base import BaseAgent
from prediction.line_monitor import line_movement_detail


class MarketIntelligenceAgent(BaseAgent):
    agent_id = "market_intelligence"
    name = "Market Intelligence Agent"

    def run(self, event: Dict[str, Any], *, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        mv = line_movement_detail(event)
        timeline = [
            {
                "line": m.get("line"),
                "opening": m.get("opening"),
                "current": m.get("current"),
                "delta": m.get("delta"),
                "signal": m.get("signal"),
            }
            for m in (mv.get("moves") or [])
        ]
        steam = [t for t in timeline if t.get("signal") == "steam"]
        return {"timeline": timeline, "steam_moves": len(steam), "detail": mv}
