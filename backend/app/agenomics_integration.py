"""
agenomics_integration.py
=========================

Интеграционный слой между PRIZOLOV SPORTS AI и Agenomics
(https://github.com/GIBDD-DPS/agenomics).

Назначение
----------
prizolov-sports-ai не поставляет "спортивные данные" в Agenomics — это
не источник данных. Вместо этого сам prizolov-sports-ai рассматривается
как ДВА автономных агента:

    1. "parser-agent"     — фоновый парсер (Forebet/Predictz/Betensured)
    2. "forecast-agent"   — движок, считающий взвешенные прогнозы (1X2,
                             тоталы, ЖК, угловые)

Этот модуль:
  - копит метрики поведения каждого агента (ошибки, срывы валидации,
    отклонение прогноза от факта, наличие логов обоснования);
  - на их основе строит `AgentGenome` для каждого агента;
  - периодически прогоняет их через `agenomics.TrustScorer`
    (и, при наличии >=2 агентов, через Compatibility Scorer, когда он
    появится в Agenomics v0.2 — см. roadmap репозитория);
  - отдаёт результат через FastAPI-эндпоинт и пишет алерт в лог, если
    Trust Score падает ниже порога.

Как подключить
---------------
1. pip install -e git+https://github.com/GIBDD-DPS/agenomics.git#egg=agenomics
   (или локально: pip install -e ../agenomics, если репозитории лежат рядом)

2. В backend/app/parser/runner.py оборачиваешь каждый прогон парсера:

       from app.agenomics_integration import PARSER_AGENT

       @PARSER_AGENT.track
       def run_parser():
           ...существующий код парсера...

3. В backend/app/services/forecast.py (или где считается прогноз)
   так же оборачиваешь функцию расчёта:

       from app.agenomics_integration import FORECAST_AGENT

       @FORECAST_AGENT.track
       def compute_forecast(match):
           ...

   А когда становится известен факт (после матча), вызываешь:

       FORECAST_AGENT.record_outcome(predicted_proba, actual_outcome)

   — это питает bias_control и drift_rate.

4. В backend/app/main.py регистрируешь роутер:

       from app.agenomics_integration import router as agenomics_router
       app.include_router(agenomics_router, prefix="/api/v1/admin")

   Появится защищённый X-Api-Secret эндпоинт:
       GET /api/v1/admin/trust
"""

from __future__ import annotations

import functools
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from statistics import mean
from typing import Callable, Deque, Optional

from fastapi import APIRouter, Header, HTTPException

try:
    from agenomics import AgentGenome, TrustScorer
except ImportError:  # позволяет модулю импортироваться даже без установленной либы,
    # чтобы не ронять весь backend, если пакет ещё не задеплоен
    AgentGenome = None
    TrustScorer = None

logger = logging.getLogger("agenomics_integration")

# ---------------------------------------------------------------------------
# Конфиг — вынеси в .env при желании
# ---------------------------------------------------------------------------
ROLLING_WINDOW = 200          # сколько последних событий держим в памяти
TRUST_ALERT_THRESHOLD = 55    # ниже этого — логируем warning/алерт
API_SECRET_ENV_VAR = "API_SECRET"


@dataclass
class _RollingMetrics:
    """Скользящее окно метрик одного агента."""

    calls: Deque[bool] = field(default_factory=lambda: deque(maxlen=ROLLING_WINDOW))          # успех/провал вызова
    validation_failures: Deque[bool] = field(default_factory=lambda: deque(maxlen=ROLLING_WINDOW))
    explained: Deque[bool] = field(default_factory=lambda: deque(maxlen=ROLLING_WINDOW))       # был ли лог обоснования
    calibration_errors: Deque[float] = field(default_factory=lambda: deque(maxlen=ROLLING_WINDOW))  # |predicted - actual|
    last_accuracy_window: Deque[float] = field(default_factory=lambda: deque(maxlen=ROLLING_WINDOW))

    def error_rate(self) -> float:
        if not self.calls:
            return 0.0
        return 1 - (sum(self.calls) / len(self.calls))

    def data_safety_score(self) -> float:
        if not self.validation_failures:
            return 100.0
        fail_rate = sum(self.validation_failures) / len(self.validation_failures)
        return round(max(0.0, 100.0 * (1 - fail_rate)), 2)

    def transparency_score(self) -> float:
        if not self.explained:
            return 50.0  # нейтральное значение, если ещё нет данных
        return round(100.0 * (sum(self.explained) / len(self.explained)), 2)

    def bias_control_score(self) -> float:
        if not self.calibration_errors:
            return 70.0
        avg_error = mean(self.calibration_errors)  # 0.0 (идеально) .. 1.0 (максимально плохо)
        return round(max(0.0, 100.0 * (1 - avg_error)), 2)

    def drift_rate(self) -> float:
        """Насколько быстро "плывёт" точность на скользящем окне (0.0 = стабильно)."""
        if len(self.last_accuracy_window) < 10:
            return 0.05  # дефолт, пока мало данных
        half = len(self.last_accuracy_window) // 2
        first_half = mean(list(self.last_accuracy_window)[:half])
        second_half = mean(list(self.last_accuracy_window)[half:])
        return round(abs(first_half - second_half), 4)


class TrackedAgent:
    """
    Обёртка вокруг одного логического агента prizolov-sports-ai
    (parser-agent или forecast-agent).
    """

    def __init__(self, agent_id: str, domain: str, autonomy: str = "autonomous"):
        self.agent_id = agent_id
        self.domain = domain
        self.autonomy = autonomy
        self.metrics = _RollingMetrics()
        self._scorer = TrustScorer() if TrustScorer else None

    # -- декоратор для оборачивания реальных функций парсера/прогноза --------
    def track(self, fn: Callable):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            start = time.monotonic()
            try:
                result = fn(*args, **kwargs)
                self.metrics.calls.append(True)
                self.metrics.validation_failures.append(False)
                return result
            except Exception as exc:  # noqa: BLE001 — сознательно широкий catch
                self.metrics.calls.append(False)
                self.metrics.validation_failures.append(True)
                logger.error(
                    "[%s] ошибка в %s: %s", self.agent_id, fn.__name__, exc, exc_info=True
                )
                raise
            finally:
                duration = time.monotonic() - start
                logger.debug("[%s] %s заняло %.3fs", self.agent_id, fn.__name__, duration)

        return wrapper

    # -- ручные хуки для мест, где декоратор неудобен (например, внутри try/except
    #    в цикле по нескольким источникам, как в runner.py) -------------------
    def record_success(self) -> None:
        self.metrics.calls.append(True)
        self.metrics.validation_failures.append(False)

    def record_failure(self, exc: Optional[Exception] = None) -> None:
        self.metrics.calls.append(False)
        self.metrics.validation_failures.append(True)
        if exc is not None:
            logger.error("[%s] зафиксирована ошибка: %s", self.agent_id, exc)

    def mark_explained(self, explained: bool = True) -> None:
        """Вызывать при формировании прогноза, если сохранён лог обоснования."""
        self.metrics.explained.append(explained)

    def record_outcome(self, predicted_proba: float, actual_outcome: int) -> None:
        """
        predicted_proba: вероятность исхода, которую выдал forecast-agent (0..1)
        actual_outcome: 1, если исход наступил, иначе 0
        Питает bias_control и drift_rate.
        """
        error = abs(predicted_proba - actual_outcome)
        self.metrics.calibration_errors.append(error)
        self.metrics.last_accuracy_window.append(1 - error)

    def build_genome(self) -> "AgentGenome":
        if AgentGenome is None:
            raise RuntimeError(
                "Пакет agenomics не установлен. "
                "pip install -e git+https://github.com/GIBDD-DPS/agenomics.git#egg=agenomics"
            )
        return AgentGenome(
            id=self.agent_id,
            domain=self.domain,
            autonomy=self.autonomy,
            transparency=self.metrics.transparency_score(),
            bias_control=self.metrics.bias_control_score(),
            data_safety=self.metrics.data_safety_score(),
            drift_rate=self.metrics.drift_rate(),
            has_ledger=False,
        )

    def score(self):
        if self._scorer is None:
            raise RuntimeError("agenomics.TrustScorer недоступен")
        genome = self.build_genome()
        result = self._scorer.score(genome)
        if result.score < TRUST_ALERT_THRESHOLD:
            logger.warning(
                "[%s] Trust Score = %.1f (%s) — ниже порога %s. capped_reason=%s",
                self.agent_id, result.score, result.label,
                TRUST_ALERT_THRESHOLD, result.capped_reason,
            )
        return result


# ---------------------------------------------------------------------------
# Два агента prizolov-sports-ai
# ---------------------------------------------------------------------------
PARSER_AGENT = TrackedAgent(
    agent_id="prizolov-parser-agent",
    domain="data-collection",
    autonomy="autonomous",   # парсер работает без ручного вмешательства (cron 30 мин)
)

FORECAST_AGENT = TrackedAgent(
    agent_id="prizolov-forecast-agent",
    domain="sports-forecasting",
    autonomy="advisory",     # прогнозы носят информационный характер (см. Disclaimer в README)
)


# ---------------------------------------------------------------------------
# FastAPI роутер
# ---------------------------------------------------------------------------
router = APIRouter(tags=["agenomics"])


def _check_secret(x_api_secret: Optional[str], expected: Optional[str]) -> None:
    if not expected or x_api_secret != expected:
        raise HTTPException(status_code=403, detail="Invalid or missing X-Api-Secret")


@router.get("/trust")
def get_trust_scores(x_api_secret: str = Header(default=None)):
    """
    GET /api/v1/admin/trust
    Header: X-Api-Secret: <API_SECRET>

    Возвращает Trust Score по обоим агентам prizolov-sports-ai.
    """
    import os

    _check_secret(x_api_secret, os.environ.get(API_SECRET_ENV_VAR))

    if TrustScorer is None:
        raise HTTPException(
            status_code=503,
            detail="agenomics не установлен на сервере",
        )

    results = {}
    for agent in (PARSER_AGENT, FORECAST_AGENT):
        try:
            r = agent.score()
            results[agent.agent_id] = {
                "score": r.score,
                "label": r.label,
                "breakdown": r.breakdown,
                "capped_reason": r.capped_reason,
            }
        except Exception as exc:  # noqa: BLE001
            results[agent.agent_id] = {"error": str(exc)}

    # Compatibility Score появится в Agenomics v0.2 (roadmap репозитория ещё не отмечен
    # как готовый) — как только он выйдет, здесь добавляется:
    #
    #   from agenomics import CompatibilityScorer
    #   compat = CompatibilityScorer().score(
    #       PARSER_AGENT.build_genome(), FORECAST_AGENT.build_genome()
    #   )
    #   results["compatibility"] = compat.score

    return results
