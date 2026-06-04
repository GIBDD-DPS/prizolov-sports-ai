# ROI / yield aggregates — bridges analytics ledger + metrics tracker.

from __future__ import annotations

from typing import Any, Dict

from analytics.roi_monitor import roi_summary as analytics_roi
from core.metrics import metrics as formulas
from core.metrics.store import load
from core.metrics.tracker import accuracy_summary, brier_summary


def combined_performance() -> Dict[str, Any]:
    state = load()
    totals = dict(state.get("totals") or {})
    stake = float(totals.get("stake_total") or 0)
    profit = float(totals.get("profit_total") or 0)
    settled = int(totals.get("wins") or 0) + int(totals.get("losses") or 0)

    tracker_roi = formulas.roi_percent(profit, stake) if stake > 0 else 0.0
    tracker_yield = formulas.yield_per_bet(profit, settled)

    analytics = analytics_roi()
    return {
        "tracker": {
            "roi_percent": tracker_roi,
            "yield_per_bet": tracker_yield,
            "profit_units": round(profit, 2),
            "stake_units": round(stake, 2),
            **accuracy_summary(),
        },
        "virtual_ledger": analytics,
        "brier": brier_summary(),
    }


def quality_dashboard() -> Dict[str, Any]:
    from core.metrics.clv import clv_all_periods

    return {
        "version": "metrics_v1",
        "performance": combined_performance(),
        "clv": clv_all_periods(),
    }
