# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.42 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""rebuild_predictions не трогает прогнозы начавшихся матчей: иначе прогноз
переписывался бы по live-коэффициентам, и сверка засчитывала бы его как
сделанный до матча."""

from datetime import UTC, datetime, timedelta

import pytest

NOW = datetime(2026, 9, 28, 12, 0, tzinfo=UTC)


@pytest.fixture()
def db():
    from app.db.base import Base
    from app.db.session import SessionLocal, engine
    import app.models  # noqa: F401
    import app.models.accuracy_log  # noqa: F401
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    session = SessionLocal()
    yield session
    session.close()


def _market_with_odds(db, kickoff, probs, tag):
    from app.models import Event, Market, Odds, Sport
    sport = db.query(Sport).filter_by(slug="football").first() or Sport(slug="football", name="Football")
    db.add(sport)
    db.flush()
    event = Event(sport_id=sport.id, home_team=f"H{tag}", away_team=f"A{tag}", kickoff_at=kickoff)
    db.add(event)
    db.flush()
    market = Market(event_id=event.id, market_type="1X2")
    db.add(market)
    db.flush()
    for selection, p in probs.items():
        db.add(Odds(market_id=market.id, source_id="the_odds_api", selection=selection, implied_prob=p))
    db.commit()
    return market


def _set_odds(db, market, probs):
    from app.models import Odds
    for row in db.query(Odds).filter(Odds.market_id == market.id):
        row.implied_prob = probs[row.selection]
    db.commit()


def test_started_match_keeps_its_pre_kickoff_forecast(db):
    from app.engine.predictor import rebuild_predictions
    from app.models import Prediction

    upcoming = _market_with_odds(db, NOW + timedelta(hours=2), {"1": 0.5, "X": 0.3, "2": 0.2}, "u")
    started = _market_with_odds(db, NOW + timedelta(minutes=10), {"1": 0.5, "X": 0.3, "2": 0.2}, "s")
    assert rebuild_predictions(db, now=NOW) == 2
    before = {p.market_id: p.selection for p in db.query(Prediction)}
    assert before == {upcoming.id: "1", started.id: "1"}

    # матч "started" начался, по ходу игры коэффициенты сменились в пользу гостей
    live = {"1": 0.1, "X": 0.2, "2": 0.7}
    _set_odds(db, started, live)
    _set_odds(db, upcoming, live)
    assert rebuild_predictions(db, now=NOW + timedelta(minutes=30)) == 1
    after = {p.market_id: p.selection for p in db.query(Prediction)}
    assert after[started.id] == "1"   # прогноз до матча не переписан
    assert after[upcoming.id] == "2"  # будущий матч обновляется как раньше


def test_match_first_seen_after_kickoff_gets_no_forecast(db):
    from app.engine.predictor import rebuild_predictions
    from app.models import Prediction

    _market_with_odds(db, NOW - timedelta(minutes=5), {"1": 0.2, "X": 0.2, "2": 0.6}, "late")
    assert rebuild_predictions(db, now=NOW) == 0
    assert db.query(Prediction).count() == 0
