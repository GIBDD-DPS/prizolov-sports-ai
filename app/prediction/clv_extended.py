# CLV: coefficient at prediction vs before kickoff.

from __future__ import annotations

import time
from typing import Any, Dict, Optional

from prediction.store import append_clv_prediction, load


def record_prediction_odds(
    event: Dict[str, Any],
    line: str,
    coefficient: float,
    *,
    bookmaker: str = "pari",
) -> Dict[str, Any]:
    from analytics.clv_tracker import compute_clv

    ek = f"{event.get('home')}|{event.get('away')}|{event.get('sport')}"
    record = {
        "ts": time.time(),
        "event_key": ek,
        "line": line,
        "bookmaker": bookmaker,
        "coef_at_prediction": round(coefficient, 3),
        "coef_pre_kickoff": None,
        "clv": None,
        "phase": "prediction",
    }
    append_clv_prediction(record)
    return record


def update_pre_kickoff(
    event_key: str,
    line: str,
    closing_coefficient: float,
) -> Optional[Dict[str, Any]]:
    from analytics.clv_tracker import compute_clv

    state = load()
    items = list(state.get("clv_predictions") or [])
    updated = None
    for item in reversed(items):
        if item.get("event_key") == event_key and item.get("line") == line and item.get("coef_pre_kickoff") is None:
            pred_coef = float(item.get("coef_at_prediction") or closing_coefficient)
            item["coef_pre_kickoff"] = round(closing_coefficient, 3)
            item["clv"] = compute_clv(pred_coef, closing_coefficient)
            item["phase"] = "pre_kickoff"
            item["updated_ts"] = time.time()
            updated = item
            break
    if updated:
        state["clv_predictions"] = items
        from prediction.store import save

        save(state)
    return updated


def clv_report(limit: int = 50) -> Dict[str, Any]:
    state = load()
    items = [i for i in (state.get("clv_predictions") or []) if i.get("clv")][-limit:]
    if not items:
        return {"samples": 0, "avg_clv_percent": 0.0, "beat_closing_rate": 0.0, "recent": []}
    clvs = [float(i["clv"].get("clv_percent", 0)) for i in items if isinstance(i.get("clv"), dict)]
    beat = sum(1 for i in items if isinstance(i.get("clv"), dict) and i["clv"].get("beat_closing"))
    return {
        "samples": len(items),
        "avg_clv_percent": round(sum(clvs) / len(clvs), 3) if clvs else 0.0,
        "beat_closing_rate": round(beat / len(items), 4),
        "recent": items[-15:],
    }
