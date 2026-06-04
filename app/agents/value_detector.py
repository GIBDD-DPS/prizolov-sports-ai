from __future__ import annotations

from typing import Any, Dict, List

from agents.base import BaseAgent
from analytics.value_detector import scan_events_for_value
from core.metrics.metrics import score_bet_display


class ValueDetectorAgent(BaseAgent):
    agent_id = "value_detector"
    name = "Value Detector"

    def run(self, event: Dict[str, Any], *, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        signals = scan_events_for_value([event], limit=5)
        top = signals[0] if signals else None
        if top:
            display = score_bet_display(
                float(top.get("model_probability") or 0.5),
                float(top.get("coefficient") or 1.5),
            )
            return {
                "value": display["value_percent"],
                "edge": display["edge"],
                "line": top.get("line"),
                "coefficient": top.get("coefficient"),
            }
        recs = event.get("recommendations") or []
        if recs:
            r = recs[0]
            display = score_bet_display(float(r.get("probability") or 0.5), float(r.get("coefficient") or 1.5))
            return {"value": display["value_percent"], "edge": display["edge"], "line": r.get("line")}
        return {"value": 0.0, "edge": False}
