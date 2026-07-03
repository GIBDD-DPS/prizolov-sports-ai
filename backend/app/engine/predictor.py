# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.40 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""Weighted prediction engine — Step 6 implementation."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.market import Market
from app.models.odds import Odds
from app.models.prediction import Prediction

SOURCE_WEIGHTS = {
    "forebet": 0.40,
    "predictz": 0.30,
    "betensured": 0.30,
}


def aggregate_source_predictions(sources: list[dict]) -> dict | None:
    """Merge normalized source predictions using configured weights."""
    if not sources:
        return None

    total_weight = 0.0
    home_prob = 0.0
    draw_prob = 0.0
    away_prob = 0.0

    for item in sources:
        source_id = item.get("source_id", "")
        weight = SOURCE_WEIGHTS.get(source_id, 0.0)
        if weight <= 0:
            continue
        total_weight += weight
        home_prob += weight * float(item.get("home_prob", 0))
        draw_prob += weight * float(item.get("draw_prob", 0))
        away_prob += weight * float(item.get("away_prob", 0))

    if total_weight == 0:
        return None

    return {
        "home_prob": round(home_prob / total_weight, 2),
        "draw_prob": round(draw_prob / total_weight, 2),
        "away_prob": round(away_prob / total_weight, 2),
        "confidence": "medium",
        "sources_used": [s.get("source_id") for s in sources],
    }


def rebuild_predictions(db: Session) -> int:
    """Rebuild aggregated 1X2 predictions from stored source odds."""
    markets = db.query(Market).filter(Market.market_type == "1X2").all()
    written = 0

    for market in markets:
        odds_rows = db.query(Odds).filter(Odds.market_id == market.id).all()
        if not odds_rows:
            continue

        by_source: dict[str, dict[str, float]] = {}
        for row in odds_rows:
            if row.selection not in {"1", "X", "2"}:
                continue
            prob = row.implied_prob
            if prob is None and row.odds_value and row.odds_value > 0:
                prob = 1.0 / row.odds_value
            if prob is None:
                continue
            by_source.setdefault(row.source_id, {})[row.selection] = float(prob)

        sources: list[dict] = []
        for source_id, vals in by_source.items():
            home = vals.get("1", 0.0)
            draw = vals.get("X", 0.0)
            away = vals.get("2", 0.0)
            total = home + draw + away
            if total <= 0:
                continue
            sources.append(
                {
                    "source_id": source_id,
                    "home_prob": home / total,
                    "draw_prob": draw / total,
                    "away_prob": away / total,
                }
            )

        aggregated = aggregate_source_predictions(sources)
        if not aggregated:
            continue

        probs = {
            "1": float(aggregated["home_prob"]),
            "X": float(aggregated["draw_prob"]),
            "2": float(aggregated["away_prob"]),
        }
        selection = max(probs, key=probs.get)
        probability = probs[selection]

        existing = db.query(Prediction).filter(Prediction.market_id == market.id).first()
        factors = {
            "home_prob": probs["1"],
            "draw_prob": probs["X"],
            "away_prob": probs["2"],
            "sources_used": aggregated.get("sources_used", []),
        }
        if existing:
            existing.selection = selection
            existing.probability = probability
            existing.confidence = str(aggregated.get("confidence", "medium"))
            existing.factors = factors
        else:
            db.add(
                Prediction(
                    event_id=market.event_id,
                    market_id=market.id,
                    selection=selection,
                    probability=probability,
                    confidence=str(aggregated.get("confidence", "medium")),
                    factors=factors,
                )
            )
        written += 1

    db.commit()
    return written
