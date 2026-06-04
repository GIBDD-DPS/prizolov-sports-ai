from analytics.clv_tracker import compute_clv
from analytics.value_detector import detect_value_in_recommendation


def test_clv_positive_when_better_odds():
    # Higher coefficient at bet time => lower implied => beat closing if closing shortens
    result = compute_clv(2.10, 1.95)
    assert result["beat_closing"] is True
    assert result["clv_percent"] > 0


def test_value_detector_edge():
    rec = {"line": "Победа 1", "coefficient": 2.0, "probability": 0.55}
    out = detect_value_in_recommendation(rec)
    assert out["edge"] > 0
    assert out["is_value"] is True
