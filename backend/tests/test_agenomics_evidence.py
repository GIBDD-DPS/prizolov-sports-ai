# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.40 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""Q4 для Agenomics: заморозка прогноза до матча и подтверждение итогом.

Запуск: cd backend && python -m pytest tests/ (нужен agenomics >= 0.9.6).
"""

from datetime import UTC, datetime, timedelta

import pytest

from app.engine import agenomics_evidence as ae

pytestmark = pytest.mark.skipif(not ae.available(), reason="нужен agenomics >= 0.9.6")

T0 = datetime(2026, 9, 27, 12, 0, tzinfo=UTC)


def _store():
    from agenomics import EvidenceStore
    return EvidenceStore(":memory:")


def _forecast(event_id=10, selection="1", prediction_id=100, market_id=20, probability=0.52):
    return {"event_id": event_id, "market_id": market_id, "prediction_id": prediction_id,
            "selection": selection, "probability": probability}


def test_task_version_roundtrip():
    tv = ae.task_version(10, 20, 100, "X", 0.3)
    assert ae.parse_task_version(tv) == {"event": 10, "market": 20, "prediction": 100, "selection": "X", "p": 0.3}
    assert ae.parse_task_version("task-v2") is None


def test_freeze_is_idempotent_and_snapshot_holds_selection():
    store = _store()
    assert ae.freeze_forecasts(store, [_forecast()], 61.0, "Conditional", "cfg", T0) == 1
    assert ae.freeze_forecasts(store, [_forecast()], 61.0, "Conditional", "cfg", T0 + timedelta(minutes=30)) == 0
    [p] = store.get_predictions(ae.AGENT_ID)
    assert p.trust_score == 61.0 and p.target == "task_failure" and p.horizon == "match_result"
    assert ae.parse_task_version(p.snapshot["task_version"])["selection"] == "1"
    assert store.verify_prediction_integrity()["violations"] == []


def test_wrong_forecast_is_q4_failure_right_forecast_is_q4_success():
    store = _store()
    ae.freeze_forecasts(store, [_forecast(event_id=10, selection="1"),
                                _forecast(event_id=11, selection="2", prediction_id=101)],
                        55.0, "Conditional", "cfg", T0)
    after = T0 + timedelta(hours=5)
    assert ae.confirm_event(store, 10, "X", "the-odds-api:scores:epl:abc:A 1-1 B", after) == 1
    assert ae.confirm_event(store, 11, "2", "the-odds-api:scores:epl:def:C 0-2 D", after) == 1
    outcomes = {ae.parse_task_version(p.snapshot["task_version"])["event"]: p.outcomes[0]
                for p in store.get_predictions(ae.AGENT_ID)}
    assert outcomes[10].occurred is True and outcomes[11].occurred is False
    assert all(o.quality_level == "Q4" and o.verification == "ground_truth" for o in outcomes.values())
    assert outcomes[10].source_reference.startswith("the-odds-api:scores:")
    # повторная сверка того же матча ничего не добавляет
    assert ae.confirm_event(store, 10, "X", "the-odds-api:scores:epl:abc:A 1-1 B", after) == 0


def test_confirmation_cannot_precede_freeze():
    store = _store()
    ae.freeze_forecasts(store, [_forecast()], 55.0, "Conditional", "cfg", T0)
    with pytest.raises(ValueError):
        ae.confirm_event(store, 10, "1", "ref", T0 - timedelta(minutes=1))


def test_validation_engine_sees_q4():
    from agenomics import validate
    store = _store()
    for i in range(3):
        ae.freeze_forecasts(store, [_forecast(event_id=i, prediction_id=i)], 50.0 + i, "Conditional", "cfg",
                            T0 + timedelta(days=i))
        ae.confirm_event(store, i, "1" if i else "2", f"ref-{i}", T0 + timedelta(days=i, hours=5))
    report = validate(store, target="task_failure")
    assert report.n_pairs == 3 and report.n_q4_pairs == 3 and report.n_positive == 1
    profile = store.evidence_profile()
    assert profile.evidence_by_quality["Q4"] == 0 and profile.outcomes_by_quality["Q4"] == 3  # Q4 у исходов
