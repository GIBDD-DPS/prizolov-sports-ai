# Post-match learning ledger and ROI by market/league analysis.

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List

from prediction.store import append_learning, load


def record_match_result(
    *,
    match: str,
    prediction: str,
    probability: float,
    result: str,
    reason: str = "",
    market: str = "",
    league: str = "",
    sport: str = "football",
) -> Dict[str, Any]:
    record = {
        "match": match,
        "prediction": prediction,
        "probability": round(probability, 4),
        "result": result,
        "reason": reason,
        "market": market,
        "league": league,
        "sport": sport,
    }
    append_learning(record)
    return record


def learning_insights() -> Dict[str, Any]:
    state = load()
    ledger: List[Dict[str, Any]] = list(state.get("learning_ledger") or [])
    if not ledger:
        return {"total": 0, "by_market": {}, "by_league": {}, "by_result": {}}

    by_market: Dict[str, List[str]] = defaultdict(list)
    by_league: Dict[str, List[str]] = defaultdict(list)
    by_result: Dict[str, int] = defaultdict(int)

    for row in ledger:
        by_result[row.get("result") or "unknown"] += 1
        by_market[row.get("market") or "unknown"].append(row.get("result") or "")
        by_league[row.get("league") or "unknown"].append(row.get("result") or "")

    def roi_proxy(results: List[str]) -> float:
        if not results:
            return 0.0
        wins = sum(1 for r in results if r in {"win", "won", "profit"})
        return round((wins / len(results)) - 0.5, 3)

    return {
        "total": len(ledger),
        "by_result": dict(by_result),
        "by_market": {k: {"samples": len(v), "roi_proxy": roi_proxy(v)} for k, v in by_market.items()},
        "by_league": {k: {"samples": len(v), "roi_proxy": roi_proxy(v)} for k, v in by_league.items()},
        "recent": ledger[-20:],
    }
