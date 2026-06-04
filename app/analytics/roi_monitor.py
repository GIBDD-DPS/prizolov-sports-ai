# Automatic ROI monitoring (virtual ledger from value signals).

from __future__ import annotations

import time
from typing import Any, Dict, List

from analytics.store import append_roi_entry, load_state


def record_virtual_bet(
    *,
    event_key: str,
    line: str,
    coefficient: float,
    model_probability: float,
    stake: float = 1.0,
    result: str = "open",
    profit: float = 0.0,
) -> Dict[str, Any]:
    entry = {
        "ts": time.time(),
        "event_key": event_key,
        "line": line,
        "coefficient": round(coefficient, 3),
        "model_probability": round(model_probability, 4),
        "stake": round(stake, 2),
        "result": result,
        "profit": round(profit, 3),
    }
    append_roi_entry(entry)
    return entry


def settle_open_bets(value_signals: List[Dict[str, Any]]) -> None:
    """Mark open virtual bets from latest scan (placeholder — manual/API settle later)."""
    state = load_state()
    open_keys = {
        (e.get("event_key"), e.get("line"))
        for e in state.get("roi_ledger") or []
        if e.get("result") == "open"
    }
    for sig in value_signals[:30]:
        key = (f"{sig.get('home')}|{sig.get('away')}|{sig.get('sport')}", sig.get("line"))
        if key in open_keys:
            continue
        record_virtual_bet(
            event_key=key[0],
            line=str(sig.get("line") or ""),
            coefficient=float(sig.get("coefficient") or 1.5),
            model_probability=float(sig.get("model_probability") or 0.5),
            result="open",
        )


def roi_summary() -> Dict[str, Any]:
    state = load_state()
    ledger: List[Dict[str, Any]] = list(state.get("roi_ledger") or [])
    if not ledger:
        return {
            "bets_total": 0,
            "open": 0,
            "settled": 0,
            "roi_percent": 0.0,
            "profit_units": 0.0,
            "yield_per_bet": 0.0,
        }
    settled = [e for e in ledger if e.get("result") != "open"]
    open_bets = [e for e in ledger if e.get("result") == "open"]
    staked = sum(float(e.get("stake") or 1) for e in settled) or 1.0
    profit = sum(float(e.get("profit") or 0) for e in settled)
    roi_pct = (profit / staked) * 100.0
    return {
        "bets_total": len(ledger),
        "open": len(open_bets),
        "settled": len(settled),
        "roi_percent": round(roi_pct, 2),
        "profit_units": round(profit, 2),
        "yield_per_bet": round(profit / max(len(settled), 1), 3),
        "recent": ledger[-15:],
    }
