# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.18 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""Сверка сохранённых прогнозов с реальными исходами матчей.

Использует эндпоинт /scores The Odds API (тот же ключ, что и для коэффициентов,
отдельная регистрация не нужна). Логика:

  1. Взять из БД события со статусом "scheduled", у которых kickoff уже прошёл
     (с запасом в пару часов, чтобы матч успел завершиться).
  2. Запросить /scores по тем же лигам за последние несколько дней.
  3. Сопоставить по названиям команд (те же строки, что источник дал при
     создании события — поставщик данных один и тот же, поэтому строки
     совпадают дословно).
  4. Определить фактический исход (1/X/2), посчитать Brier score по каждому
     сохранённому прогнозу на это событие, записать в accuracy_log,
     сообщить результат в Agenomics через FORECAST_AGENT.record_outcome().
  5. Пометить событие как "finished", чтобы не сверять его повторно.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.agenomics_integration import FORECAST_AGENT
from app.core.config import settings
from app.models.accuracy_log import AccuracyLog
from app.models.event import Event
from app.models.prediction import Prediction

BASE_URL = "https://api.the-odds-api.com"

# Не сверяем матчи раньше, чем через это время после kickoff — футбольный матч
# идёт ~2 часа, оставляем небольшой запас.
FINALIZE_DELAY = timedelta(hours=3)


def _actual_selection(home_score: int, away_score: int) -> str:
    if home_score > away_score:
        return "1"
    if home_score < away_score:
        return "2"
    return "X"


async def _fetch_scores(client: httpx.AsyncClient) -> list[dict[str, Any]]:
    response = await client.get(
        f"/v4/sports/{settings.odds_api_sport_key}/scores",
        params={
            "apiKey": settings.odds_api_key,
            "daysFrom": 3,
        },
    )
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, list):
        return []
    return data


def _parse_scores(item: dict[str, Any]) -> tuple[int, int] | None:
    if not item.get("completed"):
        return None
    scores = item.get("scores") or []
    home_team = item.get("home_team")
    away_team = item.get("away_team")
    by_team = {s.get("name"): s.get("score") for s in scores}
    home_raw = by_team.get(home_team)
    away_raw = by_team.get(away_team)
    if home_raw is None or away_raw is None:
        return None
    try:
        return int(home_raw), int(away_raw)
    except (TypeError, ValueError):
        return None


def _brier_score(probs: dict[str, float], actual: str) -> float:
    total = 0.0
    for selection in ("1", "X", "2"):
        y = 1.0 if selection == actual else 0.0
        p = probs.get(selection, 0.0)
        total += (p - y) ** 2
    return round(total, 4)


async def reconcile_finished_events(db: Session) -> int:
    """Сверяет прогнозы с фактом для завершённых матчей. Возвращает число сверенных."""
    if not settings.odds_api_key:
        return 0

    cutoff = datetime.now(tz=UTC) - FINALIZE_DELAY
    pending_events = (
        db.query(Event)
        .filter(Event.status == "scheduled", Event.kickoff_at <= cutoff)
        .all()
    )
    if not pending_events:
        return 0

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        raw_scores = await _fetch_scores(client)

    scores_by_teams: dict[tuple[str, str], tuple[int, int]] = {}
    for item in raw_scores:
        parsed = _parse_scores(item)
        if parsed is None:
            continue
        key = (str(item.get("home_team", "")).strip(), str(item.get("away_team", "")).strip())
        scores_by_teams[key] = parsed

    reconciled = 0
    for event in pending_events:
        key = (event.home_team, event.away_team)
        score = scores_by_teams.get(key)
        if score is None:
            continue  # ещё не сыгран / не найден в ответе — попробуем в следующий раз

        home_score, away_score = score
        actual = _actual_selection(home_score, away_score)

        predictions = db.query(Prediction).filter(Prediction.event_id == event.id).all()
        for prediction in predictions:
            factors = prediction.factors or {}
            probs = {
                "1": float(factors.get("home_prob", 0.0)),
                "X": float(factors.get("draw_prob", 0.0)),
                "2": float(factors.get("away_prob", 0.0)),
            }
            brier = _brier_score(probs, actual)
            correct = prediction.selection == actual

            db.add(
                AccuracyLog(
                    event_id=event.id,
                    market_id=prediction.market_id,
                    prediction_id=prediction.id,
                    predicted_selection=prediction.selection,
                    predicted_probability=prediction.probability,
                    actual_selection=actual,
                    correct=correct,
                    brier_score=brier,
                )
            )

            # FORECAST_AGENT.record_outcome ожидает: вероятность, которую агент
            # приписал СВОЕМУ выбору, и наступил ли именно этот выбор (1/0).
            FORECAST_AGENT.record_outcome(
                predicted_proba=prediction.probability,
                actual_outcome=1 if correct else 0,
            )

        event.status = "finished"
        reconciled += 1

    db.commit()
    return reconciled
