# Closing Line Value (CLV) — bet price vs closing line.

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from analytics.store import append_clv_record, load_state


def implied_probability(coefficient: float) -> float:
    if coefficient < 1.01:
        return 0.0
    return min(1.0, 1.0 / coefficient)


def compute_clv(
    bet_coefficient: float,
    closing_coefficient: float,
) -> Dict[str, Any]:
    """CLV %: positive means beat the closing line (got better price)."""
    bet_imp = implied_probability(bet_coefficient)
    close_imp = implied_probability(closing_coefficient)
    if closing_coefficient < 1.01:
        clv_pct = 0.0
    else:
        clv_pct = ((bet_coefficient / closing_coefficient) - 1.0) * 100.0
    return {
        "bet_coefficient": round(bet_coefficient, 3),
        "closing_coefficient": round(closing_coefficient, 3),
        "bet_implied": round(bet_imp, 4),
        "closing_implied": round(close_imp, 4),
        "clv_percent": round(clv_pct, 3),
        "beat_closing": bet_coefficient > closing_coefficient,
    }


def record_bet_for_clv(
    *,
    event_key: str,
    line: str,
    bet_coefficient: float,
    closing_coefficient: Optional[float] = None,
    bookmaker: str = "pari",
) -> Dict[str, Any]:
    closing = closing_coefficient if closing_coefficient else bet_coefficient
    clv = compute_clv(bet_coefficient, closing)
    record = {
        "ts": time.time(),
        "event_key": event_key,
        "line": line,
        "bookmaker": bookmaker,
        **clv,
    }
    append_clv_record(record)
    return record


def clv_summary(*, limit: int = 200) -> Dict[str, Any]:
    state = load_state()
    records: List[Dict[str, Any]] = list(state.get("clv_records") or [])[-limit:]
    if not records:
        return {
            "samples": 0,
            "avg_clv_percent": 0.0,
            "positive_clv_rate": 0.0,
            "recent": [],
        }
    avg = sum(r.get("clv_percent", 0) for r in records) / len(records)
    positive = sum(1 for r in records if r.get("beat_closing")) / len(records)
    return {
        "samples": len(records),
        "avg_clv_percent": round(avg, 3),
        "positive_clv_rate": round(positive, 4),
        "recent": records[-20:],
    }
