from __future__ import annotations

from typing import Any, Dict

from agents.base import BaseAgent
from core.metrics.roi import combined_performance
from core.metrics.tracker import record_prediction_bet, settle_bet


class ResultTrackerAgent(BaseAgent):
    agent_id = "result_tracker"
    name = "Result Tracker"

    def run(self, event: Dict[str, Any], *, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        return {"performance": combined_performance(), "event": event.get("home"), "status": "awaiting_result"}

    def record_result(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        match = str(payload.get("match") or "")
        prediction = str(payload.get("prediction") or "")
        result = str(payload.get("result") or "LOSS").upper()
        odds = float(payload.get("odds") or 2.0)
        prob = float(payload.get("probability") or 0.5)
        profit = payload.get("profit")
        if profit is None and result == "WIN":
            profit = odds - 1.0
        elif profit is None and result == "LOSS":
            profit = -1.0
        else:
            profit = float(profit or 0)

        settled = settle_bet(
            match=match,
            prediction=prediction,
            result=result,
            profit=profit,
            closing_odds=payload.get("closing_odds"),
        )
        if not settled:
            record_prediction_bet(
                match=match,
                prediction=prediction,
                odds=odds,
                probability=prob,
                opening_odds=payload.get("opening_odds"),
            )
            settled = settle_bet(match=match, prediction=prediction, result=result, profit=profit)
        return {"settled": settled, "performance": combined_performance()}
