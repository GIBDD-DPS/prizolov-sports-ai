# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.10 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""Weighted prediction engine — Step 6 implementation."""

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
