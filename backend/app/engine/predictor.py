# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.18 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""Weighted prediction engine — Step 6 implementation."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.market import Market
from app.models.odds import Odds
from app.models.prediction import Prediction

SOURCE_WEIGHTS = {
    "the_odds_api": 0.60,
    "api_football": 0.40,
    # forebet/predictz/betensured сейчас не в PARSERS (403/фейковые заглушки) —
    # веса убраны, чтобы не запутывать; вернёшь строки сюда, если снова включишь
    # эти источники в app/parser/sources/__init__.py.
}


def aggregate_source_predictions(sources: list[dict]) -> dict | None:
    """Merge normalized source predictions using configured weights."""
    if not sources:
        return None

    # Минимальный кворум источников — защита от построения прогноза на
    # единственном (потенциально сбойном) источнике данных. Сейчас активен
    # только the_odds_api, поэтому порог по умолчанию = 1; подними до 2+,
    # когда в PARSERS снова появится второй рабочий источник.
    if len(sources) < settings.min_sources_for_prediction:
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

    home_result = round(home_prob / total_weight, 2)
    draw_result = round(draw_prob / total_weight, 2)
    away_result = round(away_prob / total_weight, 2)

    return {
        "home_prob": home_result,
        "draw_prob": draw_result,
        "away_prob": away_result,
        "confidence": _estimate_confidence(sources, home_result, draw_result, away_result),
        "sources_used": [s.get("source_id") for s in sources],
    }


def _estimate_confidence(
    sources: list[dict], home_prob: float, draw_prob: float, away_prob: float
) -> str:
    """Оценка уверенности по согласию источников друг с другом.

    При одном источнике оценить "согласие" не из чего — остаётся нейтральный
    'medium'. Как только активно ≥2 источника (например, вернётся
    api_football), confidence начинает реально отражать разброс их мнений:
    маленький разброс по победившему исходу = высокая уверенность, большой = низкая.
    """
    if len(sources) < 2:
        return "medium"

    probs = {"1": home_prob, "X": draw_prob, "2": away_prob}
    winning_selection = max(probs, key=probs.get)
    key = {"1": "home_prob", "X": "draw_prob", "2": "away_prob"}[winning_selection]

    values = [float(s.get(key, 0.0)) for s in sources]
    spread = max(values) - min(values) if values else 1.0

    if spread < 0.08:
        return "high"
    if spread < 0.20:
        return "medium"
    return "low"


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
