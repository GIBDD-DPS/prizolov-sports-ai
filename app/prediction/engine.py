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
from core.system_monitor.latency import track_stage
from core.features.engine import build_features


def predict_match_outcomes(event: Dict[str, Any], *, light: bool = False) -> Dict[str, Any]:
    """
    Full pipeline for one storefront event.
    Returns 1X2 probabilities then LLM explanation.
    """
    if not light:
        record_opening_if_absent(event, "pari")

    feature_pack: Dict[str, Any] = {}
    if not light:
        with track_stage("data_collection"):
            feature_pack = build_features(event)

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

    with track_stage("ml_model"):
        ensemble = combine_ensemble(event, context)
        if not light and feature_pack:
            try:
                from models.ensemble import predict_ensemble
                ml_probs = predict_ensemble(feature_pack).get("probabilities")
                if ml_probs:
                    ep = ensemble["probabilities"]
                    for k in ep:
                        ep[k] = round(0.7 * ep[k] + 0.3 * float(ml_probs.get(k) or 0), 4)
                    t = sum(ep.values()) or 1
                    ensemble["probabilities"] = {k: round(v / t, 4) for k, v in ep.items()}
                    ensemble["ml_ensemble"] = ml_probs
            except Exception:
                pass
    probs = ensemble["probabilities"]
    quality = score_prediction(probs, event, context)
    with track_stage("llm_analysis"):
        explanation = explain_prediction(event, probs, context, quality)

    top_rec = None
    recs = event.get("all_recommendations") or event.get("recommendations") or []
    if recs and not light:
        top_rec = max(recs, key=lambda r: float(r.get("probability") or 0))
        record_prediction_odds(event, str(top_rec.get("line") or "main"), float(top_rec.get("coefficient") or 1.5))

    payload: Dict[str, Any] = {
        "match": f"{event.get('home')} vs {event.get('away')}",
        "league": event.get("league"),
        "sport": event.get("sport"),
        "home_win": probs["home_win"],
        "draw": probs["draw"],
        "away_win": probs["away_win"],
        "probabilities": probs,
        "quality": {
            "confidence": quality["confidence"],
            "confidence_label": quality["confidence_label"],
            "value": quality["value_percent"],
            "value_label": quality["value_label"],
            "risk": quality["risk"],
            "expected_roi": quality["expected_roi_percent"],
        },
        "explanation": explanation,
        "model_version": "prizolov_ensemble_v2_light" if light else "prizolov_ensemble_v2",
    }
    if not light:
        payload["ensemble"] = ensemble
        payload["features"] = feature_pack.get("ratings")
        payload["modules"] = {
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
        }
    return payload


def enrich_event_with_prediction(event: Dict[str, Any], *, light: bool = True) -> Dict[str, Any]:
    if str(event.get("sport") or "").lower() in {"esports"}:
        return event
    try:
        pred = predict_match_outcomes(event, light=light)
    except Exception:
        return event
    out = dict(event)
    out["prediction"] = pred
    return out
