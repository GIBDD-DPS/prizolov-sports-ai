# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.45 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""Связка Q4 с моделями приложения: какие прогнозы замораживаются и как
сверка матча подтверждает замороженный выбор, а не текущую строку."""

from datetime import UTC, datetime, timedelta

import pytest

from app.engine import agenomics_evidence as ae

pytestmark = pytest.mark.skipif(not ae.available(), reason="нужен agenomics >= 0.9.6")

NOW = datetime(2026, 9, 27, 12, 0, tzinfo=UTC)


@pytest.fixture()
def evidence_db(tmp_path, monkeypatch):
    """Своя база доказательств на каждый тест: номера матчей в тестах
    повторяются, и общая база смешала бы заморозки разных тестов."""
    from app.core.config import settings
    path = str(tmp_path / "agenomics_evidence.db")
    monkeypatch.setattr(settings, "agenomics_evidence_db", path)
    return path


@pytest.fixture()
def db(evidence_db):
    from app.db.base import Base
    from app.db.session import SessionLocal, engine
    import app.models  # noqa: F401  регистрирует таблицы
    import app.models.accuracy_log  # noqa: F401  не входит в app.models, в проде таблицу создаёт alembic 002
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    session = SessionLocal()
    yield session
    session.close()


def _match(db, kickoff, selection="1", market_type="1X2", status="scheduled", n=[0]):
    from app.models import Event, Market, Prediction, Sport
    n[0] += 1
    sport = db.query(Sport).filter_by(slug="football").first() or Sport(slug="football", name="Football")
    db.add(sport)
    db.flush()
    event = Event(sport_id=sport.id, home_team=f"H{n[0]}", away_team=f"A{n[0]}", kickoff_at=kickoff, status=status)
    db.add(event)
    db.flush()
    market = Market(event_id=event.id, market_type=market_type)
    db.add(market)
    db.flush()
    prediction = Prediction(event_id=event.id, market_id=market.id, selection=selection, probability=0.5,
                            factors={"home_prob": 0.5, "draw_prob": 0.3, "away_prob": 0.2})
    db.add(prediction)
    db.commit()
    return event, prediction


def _frozen(store):
    return {ae.parse_task_version(p.snapshot["task_version"])["event"]: p for p in store.get_predictions(ae.AGENT_ID)}


def test_only_upcoming_1x2_matches_in_window_are_frozen(db, evidence_db):
    soon, _ = _match(db, NOW + timedelta(minutes=30))
    later, _ = _match(db, NOW + timedelta(hours=5))
    started, _ = _match(db, NOW - timedelta(minutes=10))
    totals, _ = _match(db, NOW + timedelta(minutes=20), market_type="TOTALS")
    finished, _ = _match(db, NOW + timedelta(minutes=10), status="finished")
    assert ae.freeze_upcoming_forecasts(db, now=NOW) == 1
    assert ae.freeze_upcoming_forecasts(db, now=NOW + timedelta(minutes=5)) == 0  # уже заморожен
    store = ae.open_store(ae.evidence_db_path(evidence_db))
    try:
        assert set(_frozen(store)) == {soon.id}
    finally:
        store.close()


def test_confirmation_checks_frozen_selection_not_rewritten_row(db, evidence_db):
    event, prediction = _match(db, NOW + timedelta(minutes=30), selection="1")
    ae.freeze_upcoming_forecasts(db, now=NOW)
    prediction.selection = "X"  # парсер переписал прогноз по ходу матча
    db.commit()
    assert ae.confirm_finished_event(event.id, "X", "the-odds-api:scores:epl:id:H 1-1 A") == 1
    store = ae.open_store(ae.evidence_db_path(evidence_db))
    try:
        assert len(_frozen(store)) == 1
        outcome = _frozen(store)[event.id].outcomes[0]
        assert outcome.occurred is True  # заморожен "1", исход "X": прогноз не сбылся
        assert outcome.quality_level == "Q4"
    finally:
        store.close()


def test_reconcile_confirms_frozen_forecast_with_final_score(db, evidence_db, monkeypatch, caplog):
    """Полный путь через reconcile_finished_events: счёт из /scores (подменён)
    пишется в accuracy_log и подтверждает замороженный прогноз в agenomics."""
    import asyncio

    from app.core.config import settings
    from app.engine import accuracy
    from app.models.accuracy_log import AccuracyLog

    kickoff = datetime.now(tz=UTC) + timedelta(minutes=20)
    event, _ = _match(db, kickoff, selection="2")
    assert ae.freeze_upcoming_forecasts(db, now=datetime.now(tz=UTC)) == 1
    event.kickoff_at = datetime.now(tz=UTC) - timedelta(hours=4)  # матч сыгран
    db.commit()

    async def fake_scores(client):
        return [{"id": "evt-1", "completed": True, "home_team": event.home_team, "away_team": event.away_team,
                 "scores": [{"name": event.home_team, "score": "0"}, {"name": event.away_team, "score": "2"}]}]

    monkeypatch.setattr(settings, "odds_api_key", "test-key")
    monkeypatch.setattr(accuracy, "_fetch_scores", fake_scores)
    caplog.set_level("INFO")
    assert asyncio.run(accuracy.reconcile_finished_events(db)) == 1
    assert db.query(AccuracyLog).one().correct is True

    store = ae.open_store(ae.evidence_db_path(evidence_db))
    try:
        outcome = _frozen(store)[event.id].outcomes[0]
        assert outcome.occurred is False and outcome.quality_level == "Q4"
        assert "evt-1" in outcome.source_reference and "0-2" in outcome.source_reference
    finally:
        store.close()
    assert any("Agenomics Q4: подтверждено прогнозов 1 по 1 матчам из 1 сверенных" in r.getMessage()
               for r in caplog.records)


def test_evidence_status_summary(db, evidence_db):
    status = ae.evidence_status(evidence_db)
    assert status["exists"] is False and "frozen_predictions" not in status  # файла нет и он не создаётся
    assert not __import__("os").path.exists(evidence_db)
    confirmed, _ = _match(db, NOW + timedelta(minutes=30), selection="1")
    _match(db, NOW + timedelta(minutes=40), selection="2")
    assert ae.freeze_upcoming_forecasts(db, now=NOW) == 2
    ae.confirm_finished_event(confirmed.id, "1", "the-odds-api:scores:epl:id:H 1-0 A")
    status = ae.evidence_status(evidence_db)
    assert status["exists"] and status["agenomics_available"]
    assert (status["frozen_predictions"], status["confirmed_q4"], status["awaiting_result"]) == (2, 1, 1)
    assert (status["forecast_correct"], status["forecast_wrong"]) == (1, 0)
    assert status["last_frozen_at"] and status["last_confirmed_at"]
    # проверка Q4: только подтверждённые счётом пары; два матча, один ещё не сыгран
    q4 = status["q4_validation"]
    assert "error" not in q4, q4
    assert q4["pairs"] == 1 and q4["forecast_wrong"] == 0 and q4["verdict"] == "insufficient_data"
    assert q4["independence_groups"] == ["the_odds_api_scores"] and q4["claim_level"] == "exploratory"
    recent = status["recent_confirmations"]
    assert len(recent) == 1 and recent[0]["event_id"] == confirmed.id and recent[0]["forecast_correct"] is True
    assert recent[0]["frozen_selection"] == "1" and recent[0]["trust_score_at_freeze"] is not None
    assert status["trust_score_at_freeze"]["min"] <= status["trust_score_at_freeze"]["max"]
    assert status["scorecard"]["evidence_q4"]["current"] == 1


def test_admin_agenomics_endpoint(db, evidence_db, monkeypatch):
    from fastapi.testclient import TestClient

    from app.api.routes import admin
    from app.core.config import settings
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(admin.router, prefix="/api/v1")
    client = TestClient(app)
    monkeypatch.setattr(settings, "api_secret", "s3cret")
    assert client.get("/api/v1/admin/agenomics").status_code == 403
    _match(db, NOW + timedelta(minutes=30))
    ae.freeze_upcoming_forecasts(db, now=NOW)
    body = client.get("/api/v1/admin/agenomics", headers={"X-Api-Secret": "s3cret"}).json()
    assert body["evidence_db"] == evidence_db and body["frozen_predictions"] == 1 and body["confirmed_q4"] == 0
