# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.28 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""Persist parsed events and odds into PostgreSQL."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.event import Event
from app.models.market import Market
from app.models.odds import Odds
from app.models.parse_log import ParseLog
from app.models.parse_source import ParseSource
from app.models.sport import Sport


def _ensure_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        raw = value.strip()
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(raw)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except ValueError:
            pass
    return datetime.now(tz=UTC)


def _find_or_create_event(db: Session, sport_id: int, payload: dict[str, Any]) -> Event:
    kickoff_at = _ensure_datetime(payload.get("kickoff"))
    home_team = str(payload.get("home_team", "")).strip()[:128]
    away_team = str(payload.get("away_team", "")).strip()[:128]
    league = str(payload.get("league", "")).strip()[:128]

    event = (
        db.query(Event)
        .filter(
            Event.sport_id == sport_id,
            Event.home_team == home_team,
            Event.away_team == away_team,
            Event.kickoff_at == kickoff_at,
        )
        .first()
    )
    if event:
        event.league = league
        event.status = "scheduled"
        return event

    event = Event(
        sport_id=sport_id,
        home_team=home_team,
        away_team=away_team,
        league=league,
        kickoff_at=kickoff_at,
        status="scheduled",
    )
    db.add(event)
    db.flush()
    return event


def _find_or_create_market(db: Session, event_id: int, payload: dict[str, Any]) -> Market:
    market_type = str(payload.get("market_type", "1X2")).strip()[:32] or "1X2"
    line_value = payload.get("line_value")

    query = db.query(Market).filter(
        Market.event_id == event_id,
        Market.market_type == market_type,
    )
    if line_value is None:
        query = query.filter(Market.line_value.is_(None))
    else:
        query = query.filter(Market.line_value == float(line_value))

    market = query.first()
    if market:
        return market

    market = Market(
        event_id=event_id,
        market_type=market_type,
        line_value=float(line_value) if line_value is not None else None,
    )
    db.add(market)
    db.flush()
    return market


def _upsert_odd(
    db: Session,
    market_id: int,
    source_id: str,
    selection: str,
    odds_value: float | None,
) -> None:
    odd = (
        db.query(Odds)
        .filter(
            Odds.market_id == market_id,
            Odds.source_id == source_id,
            Odds.selection == selection,
        )
        .first()
    )
    implied_prob = (1.0 / odds_value) if odds_value and odds_value > 0 else None
    if odd:
        odd.odds_value = odds_value
        odd.implied_prob = implied_prob
        odd.fetched_at = datetime.now(tz=UTC)
        return

    db.add(
        Odds(
            market_id=market_id,
            source_id=source_id,
            selection=selection,
            odds_value=odds_value,
            implied_prob=implied_prob,
        )
    )


def persist_source_events(source_id: str, events: list[dict[str, Any]]) -> int:
    db = SessionLocal()
    started_at = datetime.now(tz=UTC)
    try:
        sport = db.query(Sport).filter(Sport.slug == "football").first()
        if not sport:
            raise RuntimeError("Sport 'football' not found")

        written = 0
        for payload in events:
            if not payload.get("home_team") or not payload.get("away_team"):
                continue
            event = _find_or_create_event(db, sport.id, payload)
            markets = payload.get("markets") or []
            for market_payload in markets:
                market = _find_or_create_market(db, event.id, market_payload)
                for odd_payload in market_payload.get("selections") or []:
                    selection = str(odd_payload.get("selection", "")).strip()[:32]
                    if not selection:
                        continue
                    odds_raw = odd_payload.get("odds_value")
                    odds_value = float(odds_raw) if odds_raw is not None else None
                    _upsert_odd(db, market.id, source_id, selection, odds_value)
            written += 1

        parse_source = db.query(ParseSource).filter(ParseSource.source_id == source_id).first()
        if parse_source:
            parse_source.last_ok_at = datetime.now(tz=UTC)
            parse_source.last_error = None

        db.add(
            ParseLog(
                source_id=source_id,
                status="ok",
                items_fetched=written,
                message=f"Persisted events: {written}",
                started_at=started_at,
                finished_at=datetime.now(tz=UTC),
            )
        )
        db.commit()
        return written
    except Exception as exc:
        db.rollback()
        parse_source = db.query(ParseSource).filter(ParseSource.source_id == source_id).first()
        if parse_source:
            parse_source.last_error = str(exc)[:4000]
        db.add(
            ParseLog(
                source_id=source_id,
                status="error",
                items_fetched=0,
                message=str(exc)[:4000],
                started_at=started_at,
                finished_at=datetime.now(tz=UTC),
            )
        )
        db.commit()
        raise
    finally:
        db.close()


def persist_source_error(source_id: str, message: str) -> None:
    db = SessionLocal()
    now = datetime.now(tz=UTC)
    try:
        parse_source = db.query(ParseSource).filter(ParseSource.source_id == source_id).first()
        if parse_source:
            parse_source.last_error = message[:4000]
        db.add(
            ParseLog(
                source_id=source_id,
                status="error",
                items_fetched=0,
                message=message[:4000],
                started_at=now,
                finished_at=now,
            )
        )
        db.commit()
    finally:
        db.close()
