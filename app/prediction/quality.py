# Confidence, Value, Risk, Expected ROI scores.

from __future__ import annotations

from typing import Any, Dict


def score_prediction(
    probabilities: Dict[str, float],
    event: Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    h = float(probabilities.get("home_win") or 0)
    d = float(probabilities.get("draw") or 0)
    a = float(probabilities.get("away_win") or 0)
    top = max(h, d, a)
    second = sorted([h, d, a], reverse=True)[1]
    margin = top - second

    lineup = context.get("lineup") or {}
    line_mv = context.get("line_movement") or {}
    moves = len(line_mv.get("moves") or [])

    confidence = min(100, int(40 + margin * 120 + (lineup.get("confidence_multiplier") or 1) * 15))

    recs = event.get("all_recommendations") or event.get("recommendations") or []
    best_coef = 1.9
    best_prob = top
    if recs:
        best = max(recs, key=lambda r: float(r.get("probability") or 0))
        best_coef = float(best.get("coefficient") or 1.9)
        best_prob = float(best.get("adjusted_probability", best.get("probability")) or top)

    implied = 1.0 / best_coef if best_coef >= 1.01 else 0.5
    value_pct = round((best_prob - implied) * 100, 2)
    ev = best_prob * best_coef - 1.0
    expected_roi = round(ev * 100, 2)

    risk = "low"
    if moves >= 3 or (lineup.get("risk_flags")):
        risk = "medium"
    if not lineup.get("lineup_confirmed") and str(event.get("sport")) in {"football", "basketball", "tennis"}:
        risk = "high" if moves >= 2 else "medium"

    return {
        "confidence": confidence,
        "confidence_label": f"{confidence}/100",
        "value_percent": value_pct,
        "value_label": f"{value_pct:+.1f}%",
        "risk": risk,
        "expected_roi_percent": expected_roi,
        "top_outcome": "home_win" if top == h else ("draw" if top == d else "away_win"),
    }
