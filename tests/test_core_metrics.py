"""Tests for core metrics and quality scoring."""

from __future__ import annotations

from core.metrics.metrics import brier_score, expected_value_percent, score_bet_display, value_percent
from core.metrics.tracker import record_prediction_bet, settle_bet, accuracy_summary


def test_brier_score():
    assert brier_score(0.7, 1) == 0.09
    assert brier_score(0.7, 0) == 0.49


def test_score_bet_display_has_kelly_and_ev():
    d = score_bet_display(0.62, 1.85)
    assert d["confidence"] >= 0
    assert "expected_value_percent" in d
    assert d["risk"] in {"LOW", "MEDIUM", "HIGH"}
    assert d["kelly_stake_percent"] >= 0


def test_tracker_settle_updates_accuracy():
    record_prediction_bet(match="X vs Y", prediction="П1", odds=2.05, probability=0.67)
    settled = settle_bet(match="X vs Y", prediction="П1", result="WIN", profit=1.05)
    assert settled is not None
    acc = accuracy_summary()
    assert acc["wins"] >= 1
