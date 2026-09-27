# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.40 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""Внешнее подтверждение исходов для Agenomics (уровень Q4).

Прогноз 1X2 проверяется реальностью: итогом матча из внешнего источника.
Это первый источник Q4 для Agenomics (docs/VALIDATION_PROTOCOL.md,
раздел 7, в репозитории agenomics).

Два шага:

1. **Заморозка до начала матча** (freeze_upcoming_forecasts, из runner
   после пересчёта прогнозов). Для матчей, которые начнутся в ближайшее
   окно, в EvidenceStore agenomics пишется наблюдение с текущим Trust
   Score прогнозирующего агента и предсказание цели task_failure
   («прогноз не сбудется»). Выбранный исход и его вероятность входят в
   снимок предсказания (task_version) и защищены SHA-256 снимка. Сама
   строка predictions в этой базе после этого может меняться (парсер
   переписывает её каждый прогон, в том числе по live-коэффициентам), но
   проверяется именно замороженный выбор.

2. **Подтверждение после матча** (confirm_event, из reconcile в
   accuracy.py). Итоговый счёт из The Odds API /scores подтверждает или
   опровергает замороженный выбор через agenomics.record_external_outcome():
   Trust Score верификатору не передаётся, подтверждение строго позже
   заморозки, донор результатов в своей группе независимости.

Если матч пропущен окном заморозки (например, сервис был выключен), он
не замораживается задним числом: Q4 по нему просто нет.

Любая ошибка здесь логируется и не прерывает парсер и сверку.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

logger = logging.getLogger("prizolov.agenomics_evidence")

try:
    import agenomics
    from agenomics import EvidenceStore, ExternalVerification, record_external_outcome
except ImportError:  # agenomics < 0.9.6 или не установлен
    agenomics = None
    EvidenceStore = ExternalVerification = record_external_outcome = None

AGENT_ID = "prizolov-forecast-agent"
TARGET = "task_failure"          # прогноз не сбылся
HORIZON = "match_result"
TASK_PREFIX = "sports-1x2"
ENGINE_VERSION = "prizolov-weighted-1x2-v1"
ENVIRONMENT_ID = "amvera/prizolov-sports"

RESULTS_DONOR = dict(
    donor_id="prizolov.match_results.the_odds_api",
    donor_type="outcome",
    name="The Odds API /scores: итоговый счёт матча",
    independence_group="the_odds_api_scores",
    provider="the-odds-api.com",
)

_TASK_RE = re.compile(
    rf"^{TASK_PREFIX}:event=(?P<event>\d+);market=(?P<market>\d+);prediction=(?P<prediction>\d+);"
    r"selection=(?P<selection>[1X2]);p=(?P<p>[0-9.]+)$"
)


def available() -> bool:
    return record_external_outcome is not None


def evidence_db_path(configured: str = "") -> str:
    """Файл базы доказательств. На Amvera /data это persistenceMount:
    переживает перезапуски и деплои."""
    if configured:
        return configured
    return "/data/agenomics_evidence.db" if Path("/data").is_dir() else "agenomics_evidence.db"


def task_version(event_id: int, market_id: int, prediction_id: int, selection: str, probability: float) -> str:
    return (f"{TASK_PREFIX}:event={event_id};market={market_id};prediction={prediction_id};"
            f"selection={selection};p={probability:.4f}")


def parse_task_version(value: Optional[str]) -> Optional[dict]:
    match = _TASK_RE.match(value or "")
    if not match:
        return None
    info = match.groupdict()
    return {"event": int(info["event"]), "market": int(info["market"]),
            "prediction": int(info["prediction"]), "selection": info["selection"], "p": float(info["p"])}


def configuration_hash(source_weights: dict, min_sources: int) -> str:
    """Конфигурация прогнозирующего агента: движок, веса источников, кворум.
    Меняется только при смене конфигурации, а не с каждой метрикой."""
    payload = {"engine": ENGINE_VERSION, "weights": source_weights, "min_sources": min_sources}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]


def _frozen_keys(store) -> set:
    keys = set()
    for p in store.get_predictions(AGENT_ID):
        info = parse_task_version(p.snapshot.get("task_version"))
        if info:
            keys.add((info["event"], info["market"], info["prediction"]))
    return keys


def freeze_forecasts(store, forecasts: Iterable[dict], trust_score: float, trust_label: str,
                     config_hash: str, now: datetime) -> int:
    """Замораживает прогнозы, ещё не замороженные. forecasts: словари с
    event_id, market_id, prediction_id, selection, probability. Одно
    наблюдение на прогноз: у каждого матча свой замороженный Trust Score.
    Возвращает число новых замороженных предсказаний."""
    already = _frozen_keys(store)
    frozen = 0
    for f in forecasts:
        key = (f["event_id"], f["market_id"], f["prediction_id"])
        if key in already:
            continue
        obs_id = store.record_observation(
            AGENT_ID, trust_score, trust_label, genome_hash=config_hash,
            model_version=ENGINE_VERSION, source="prizolov-sports-ai/pre-kickoff", timestamp=now,
        )
        store.record_prediction(
            obs_id, TARGET, horizon=HORIZON, frozen_at=now,
            task_version=task_version(f["event_id"], f["market_id"], f["prediction_id"],
                                      f["selection"], float(f["probability"])),
            environment_id=ENVIRONMENT_ID,
        )
        already.add(key)
        frozen += 1
    return frozen


class MatchResultVerifier:
    """Верификатор одного завершённого матча. Получает от agenomics
    предсказание без Trust Score и сравнивает замороженный выбор с
    фактическим исходом."""

    donor_id = RESULTS_DONOR["donor_id"]

    def __init__(self, event_id: int, actual_selection: str, source_reference: str, observed_at: datetime):
        self.event_id = event_id
        self.actual_selection = actual_selection
        self.source_reference = source_reference
        self.observed_at = observed_at

    def verify(self, prediction):
        info = parse_task_version(prediction.task_version)
        if info is None or info["event"] != self.event_id:
            return None
        return ExternalVerification(
            occurred=info["selection"] != self.actual_selection,
            outcome_type="task_failure",
            source_type="external_system",
            source_reference=self.source_reference,
            verification_method="api_assertion",
            verified_at=self.observed_at,
        )


def confirm_event(store, event_id: int, actual_selection: str, source_reference: str, now: datetime) -> int:
    """Подтверждает все замороженные прогнозы матча. Уже подтверждённые
    пропускаются. Возвращает число записанных исходов Q4."""
    store.register_donor(**RESULTS_DONOR)
    verifier = MatchResultVerifier(event_id, actual_selection, source_reference, now)
    confirmed = 0
    for p in store.get_predictions(AGENT_ID):
        info = parse_task_version(p.snapshot.get("task_version"))
        if info is None or info["event"] != event_id:
            continue
        if any(o.donor_id == RESULTS_DONOR["donor_id"] for o in p.outcomes):
            continue
        if record_external_outcome(store, p.id, verifier) is not None:
            confirmed += 1
    return confirmed


def open_store(configured_path: str = ""):
    """EvidenceStore или None, если agenomics недоступен нужной версии."""
    if not available():
        logger.warning("agenomics >= 0.9.6 не установлен: Q4 не пишется")
        return None
    return EvidenceStore(evidence_db_path(configured_path))


# --- Связка с приложением ------------------------------------------------------

def freeze_upcoming_forecasts(db, now: Optional[datetime] = None) -> int:
    """Из runner после rebuild_predictions: замораживает прогнозы 1X2 на
    матчи, которые начнутся в ближайшее окно (agenomics_freeze_window_minutes)."""
    from datetime import UTC, timedelta

    from app.agenomics_integration import FORECAST_AGENT
    from app.core.config import settings
    from app.engine.predictor import SOURCE_WEIGHTS
    from app.models.event import Event
    from app.models.market import Market
    from app.models.prediction import Prediction

    now = now or datetime.now(tz=UTC)
    window_end = now + timedelta(minutes=settings.agenomics_freeze_window_minutes)
    rows = (
        db.query(Prediction, Event)
        .join(Event, Prediction.event_id == Event.id)
        .join(Market, Prediction.market_id == Market.id)
        .filter(Market.market_type == "1X2", Event.status == "scheduled",
                Event.kickoff_at > now, Event.kickoff_at <= window_end)
        .all()
    )
    if not rows:
        return 0
    store = open_store(settings.agenomics_evidence_db)
    if store is None:
        return 0
    try:
        trust = FORECAST_AGENT.score()  # до матча, только из прошлых исходов
        forecasts = [
            {"event_id": e.id, "market_id": p.market_id, "prediction_id": p.id,
             "selection": p.selection, "probability": p.probability}
            for p, e in rows
        ]
        return freeze_forecasts(store, forecasts, trust.score, trust.label,
                                configuration_hash(SOURCE_WEIGHTS, settings.min_sources_for_prediction), now)
    finally:
        store.close()


def confirm_finished_event(event_id: int, actual_selection: str, source_reference: str) -> int:
    """Из reconcile_finished_events: подтверждает замороженные прогнозы
    матча его итоговым счётом."""
    from datetime import UTC

    from app.core.config import settings

    store = open_store(settings.agenomics_evidence_db)
    if store is None:
        return 0
    try:
        return confirm_event(store, event_id, actual_selection, source_reference, datetime.now(tz=UTC))
    finally:
        store.close()
