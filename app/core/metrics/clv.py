# CLV with period breakdown (day / week / month / all).

from __future__ import annotations

import time
from typing import Any, Dict, List

from analytics.clv_tracker import clv_summary as analytics_clv_summary
from analytics.clv_tracker import compute_clv, record_bet_for_clv


def record_opening_clv(
    *,
    event_key: str,
    line: str,
    opening_odds: float,
    closing_odds: float | None = None,
    bookmaker: str = "pari",
) -> Dict[str, Any]:
    closing = closing_odds if closing_odds is not None else opening_odds
    return record_bet_for_clv(
        event_key=event_key,
        line=line,
        bet_coefficient=opening_odds,
        closing_coefficient=closing,
        bookmaker=bookmaker,
    )


def _filter_by_period(records: List[Dict[str, Any]], period: str) -> List[Dict[str, Any]]:
    now = time.time()
    windows = {
        "day": 86400,
        "week": 7 * 86400,
        "month": 30 * 86400,
        "all": None,
    }
    sec = windows.get(period)
    if sec is None:
        return records
    cutoff = now - sec
    return [r for r in records if float(r.get("ts") or 0) >= cutoff]


def clv_by_period(*, period: str = "all", limit: int = 500) -> Dict[str, Any]:
    base = analytics_clv_summary(limit=limit)
    records: List[Dict[str, Any]] = list(base.get("recent") or [])
    try:
        from analytics.store import load_state

        records = list(load_state().get("clv_records") or [])[-limit:]
    except Exception:
        pass

    filtered = _filter_by_period(records, period)
    if not filtered:
        return {
            "period": period,
            "samples": 0,
            "avg_clv_percent": 0.0,
            "positive_clv_rate": 0.0,
            "recent": [],
        }
    avg = sum(r.get("clv_percent", 0) for r in filtered) / len(filtered)
    positive = sum(1 for r in filtered if r.get("beat_closing")) / len(filtered)
    return {
        "period": period,
        "samples": len(filtered),
        "avg_clv_percent": round(avg, 3),
        "positive_clv_rate": round(positive, 4),
        "recent": filtered[-15:],
    }


def clv_all_periods() -> Dict[str, Any]:
    return {p: clv_by_period(period=p) for p in ("day", "week", "month", "all")}
