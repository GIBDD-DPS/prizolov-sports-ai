"""Tests for probabilistic 1X2 prediction ensemble."""

from __future__ import annotations

import pytest

pytest.importorskip("numpy")

from prediction.engine import predict_match_outcomes, enrich_event_with_prediction
from prediction.learning import record_match_result, learning_insights


def _football_event(**overrides):
    base = {
        "sport": "football",
        "league": "Test League",
        "home": "Team Alpha",
        "away": "Team Beta",
        "recommendations": [
            {"line": "Победа 1", "coefficient": 2.1, "probability": 0.58},
            {"line": "Ничья", "coefficient": 3.4, "probability": 0.22},
            {"line": "Победа 2", "coefficient": 3.0, "probability": 0.35},
        ],
    }
    base.update(overrides)
    return base


def test_predict_match_outcomes_returns_1x2_probabilities():
    result = predict_match_outcomes(_football_event())
    for key in ("home_win", "draw", "away_win"):
        assert key in result
        assert 0.0 <= result[key] <= 1.0
    total = result["home_win"] + result["draw"] + result["away_win"]
    assert abs(total - 1.0) < 0.02
    assert "explanation" in result
    assert result["quality"]["confidence"] >= 0


def test_enrich_event_attaches_prediction():
    event = _football_event()
    enriched = enrich_event_with_prediction(event)
    assert "prediction" in enriched
    assert enriched["prediction"]["home_win"] > 0


def test_learning_ledger_record():
    record_match_result(
        match="A vs B",
        prediction="home_win",
        probability=0.67,
        result="loss",
        reason="red_card",
        market="1x2",
        league="Test",
    )
    insights = learning_insights()
    assert insights["total"] >= 1
    assert insights["recent"][-1]["reason"] == "red_card"
