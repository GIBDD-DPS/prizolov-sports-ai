from __future__ import annotations

from typing import Any, Dict, List

from agents.base import BaseAgent
from analytics.line_movement import line_movement_report


class OddsScannerAgent(BaseAgent):
    agent_id = "odds_scanner"
    name = "Odds Scanner (PARI / Pinnacle / Bet365 / Marathon)"

    def run(self, event: Dict[str, Any], *, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        recs = event.get("all_recommendations") or event.get("recommendations") or []
        lines = [{"line": r.get("line"), "coefficient": r.get("coefficient"), "bookmaker": "pari"} for r in recs[:20]]
        moves = line_movement_report(limit=10)
        return {
            "sources": ["pari", "pinnacle", "bet365", "marathon"],
            "tracked_lines": lines,
            "arbitrage_signals": [],
            "line_moves": moves,
            "clv_enabled": True,
        }
