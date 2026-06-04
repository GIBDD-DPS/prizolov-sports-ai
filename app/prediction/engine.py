# Main prediction engine — probabilistic 1X2 + ensemble + quality + explanation.

from __future__ import annotations

from typing import Any, Dict, Optional

from prediction.calendar_strength import assess_calendar
from prediction.clv_extended import record_prediction_odds
from prediction.elo import elo_context
from prediction.ensemble import combine_ensemble
from prediction.explain import explain_prediction
from prediction.learning import learning_insights
from prediction.line_monitor import line_movement_detail, record_opening_if_absent
from prediction.lineup import assess_lineup_risk
from prediction.motivation import motivation_context
from prediction.quality import score_prediction
from prediction.referee import from_event as referee_from_event
from prediction.weather import weather_context
from prediction.xg_football import build_football_xg_profile
from prediction.clv_extended import clv_report


def predict_match_outcomes(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Full pipeline for one storefront event.
    Returns 1X2 probabilities then LLM explanation.
    """
    record_opening_if_absent(event, "pari")

    context: Dict[str, Any] = {
        "elo": elo_context(event),
        "xg_profile": build_football_xg_profile(event, event.get("xg_stats")),
        "lineup": assess_lineup_risk(event),
        "calendar": assess_calendar(event),
        "referee": referee_from_event(event),
        "weather": weather_context(event),
        "motivation": motivation_context(event),
        "line_movement": line_movement_detail(event),
    }

    ensemble = combine_ensemble(event, context)
    probs = ensemble["probabilities"]
    quality = score_prediction(probs, event, context)
    explanation = explain_prediction(event, probs, context, quality)

    top_rec = None
    recs = event.get("all_recommendations") or event.get("recommendations") or []
    if recs:
        top_rec = max(recs, key=lambda r: float(r.get("probability") or 0))
        record_prediction_odds(event, str(top_rec.get("line") or "main"), float(top_rec.get("coefficient") or 1.5))

    return {
        "match": f"{event.get('home')} vs {event.get('away')}",
        "league": event.get("league"),
        "sport": event.get("sport"),
        "home_win": probs["home_win"],
        "draw": probs["draw"],
        "away_win": probs["away_win"],
        "probabilities": probs,
        "ensemble": ensemble,
        "quality": {
            "confidence": quality["confidence"],
            "confidence_label": quality["confidence_label"],
            "value": quality["value_percent"],
            "value_label": quality["value_label"],
            "risk": quality["risk"],
            "expected_roi": quality["expected_roi_percent"],
        },
        "explanation": explanation,
        "modules": {
            "xg_football": context["xg_profile"],
            "elo": context["elo"],
            "lineup": context["lineup"],
            "calendar": context["calendar"],
            "referee": context["referee"],
            "weather": context["weather"],
            "motivation": context["motivation"],
            "line_movement": context["line_movement"],
            "clv": clv_report(),
            "learning": learning_insights(),
        },
        "model_version": "prizolov_ensemble_v1",
    }


def enrich_event_with_prediction(event: Dict[str, Any]) -> Dict[str, Any]:
    if str(event.get("sport") or "").lower() in {"esports"}:
        return event
    try:
        pred = predict_match_outcomes(event)
    except Exception:
        return event
    out = dict(event)
    out["prediction"] = pred
    return out
