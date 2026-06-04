from __future__ import annotations

from typing import Any, Dict


def run(event: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, float]:
    """Placeholder: map sentiment / news bias to 1X2 tilt."""
    sentiment = event.get("news_sentiment") or context.get("news_sentiment") or {}
    home_bias = float(sentiment.get("home_bias") or 0.0)
    away_bias = float(sentiment.get("away_bias") or 0.0)
    base = {"home_win": 0.40, "draw": 0.27, "away_win": 0.33}
    base["home_win"] = max(0.05, min(0.85, base["home_win"] + home_bias))
    base["away_win"] = max(0.05, min(0.85, base["away_win"] + away_bias))
    base["draw"] = max(0.05, 1.0 - base["home_win"] - base["away_win"])
    total = base["home_win"] + base["draw"] + base["away_win"]
    return {k: round(v / total, 4) for k, v in base.items()}
