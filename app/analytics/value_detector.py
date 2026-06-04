# Value Detector — model probability vs market implied probability (edge).

from __future__ import annotations

from typing import Any, Dict, List


def detect_value_in_recommendation(rec: Dict[str, Any]) -> Dict[str, Any]:
    coef = float(rec.get("coefficient") or 1.01)
    prob = float(rec.get("adjusted_probability", rec.get("probability", 0)) or 0)
    implied = min(1.0, 1.0 / coef) if coef >= 1.01 else 0.0
    edge = prob - implied
    ev = (prob * coef) - 1.0
    is_value = edge > 0.02 and ev > 0.03 and coef >= 1.4
    return {
        "line": rec.get("line"),
        "coefficient": round(coef, 3),
        "model_probability": round(prob, 4),
        "implied_probability": round(implied, 4),
        "edge": round(edge, 4),
        "expected_value": round(ev, 4),
        "is_value": is_value,
        "confidence": rec.get("confidence", "med"),
    }


def scan_events_for_value(
    events: List[Dict[str, Any]],
    *,
    min_edge: float = 0.02,
    min_coefficient: float = 1.4,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    signals: List[Dict[str, Any]] = []
    for event in events:
        pool = event.get("all_recommendations") or event.get("recommendations") or []
        for rec in pool:
            if float(rec.get("coefficient") or 0) < min_coefficient:
                continue
            analysis = detect_value_in_recommendation(rec)
            if analysis["edge"] < min_edge:
                continue
            signals.append(
                {
                    "event_id": event.get("id"),
                    "sport": event.get("sport"),
                    "league": event.get("league"),
                    "home": event.get("home"),
                    "away": event.get("away"),
                    "time": event.get("time"),
                    "is_live": event.get("is_live"),
                    "xg_metrics": event.get("xg_metrics"),
                    **analysis,
                }
            )
    signals.sort(key=lambda s: (-s["edge"], -s["expected_value"]))
    return signals[:limit]
