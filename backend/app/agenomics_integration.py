"""
agenomics_integration.py
=========================

Интеграционный слой между PRIZOLOV SPORTS AI и Agenomics
(https://github.com/GIBDD-DPS/agenomics).
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

from app.core.config import settings

try:
    from agenomics import AgentGenome, TrustScorer
except ImportError:
    AgentGenome = None
    TrustScorer = None

logger = logging.getLogger("agenomics_integration")

ROLLING_WINDOW = 200
TRUST_ALERT_THRESHOLD = 55


@dataclass
class _RollingMetrics:
    calls: Deque[bool] = field(default_factory=lambda: deque(maxlen=ROLLING_WINDOW))
    validation_failures: Deque[bool] = field(default_factory=lambda: deque(maxlen=ROLLING_WINDOW))
    explained: Deque[bool] = field(default_factory=lambda: deque(maxlen=ROLLING_WINDOW))
    calibration_errors: Deque[float] = field(default_factory=lambda: deque(maxlen=ROLLING_WINDOW))
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
            return 50.0
        return round(100.0 * (sum(self.explained) / len(self.explained)), 2)

    def bias_control_score(self) -> float:
        if not self.calibration_errors:
            return 70.0
        avg_error = mean(self.calibration_errors)
        return round(max(0.0, 100.0 * (1 - avg_error)), 2)

    def drift_rate(self) -> float:
        if len(self.last_accuracy_window) < 10:
            return 0.05
        half = len(self.last_accuracy_window) // 2
        first_half = mean(list(self.last_accuracy_window)[:half])
        second_half = mean(list(self.last_accuracy_window)[half:])
        return round(abs(first_half - second_half), 4)


class TrackedAgent:
    def __init__(self, agent_id: str, domain: str, autonomy: str = "autonomous"):
        self.agent_id = agent_id
        self.domain = domain
        self.autonomy = autonomy
        self.metrics = _RollingMetrics()
        self._scorer = TrustScorer() if TrustScorer else None

    def track(self, fn: Callable):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            start = time.monotonic()
            try:
                result = fn(*args, **kwargs)
                self.metrics.calls.append(True)
                self.metrics.validation_failures.append(False)
                return result
            except Exception as exc:
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

    def record_success(self) -> None:
        self.metrics.calls.append(True)
        self.metrics.validation_failures.append(False)

    def record_failure(self, exc: Optional[Exception] = None) -> None:
        self.metrics.calls.append(False)
        self.metrics.validation_failures.append(True)
        if exc is not None:
            logger.error("[%s] зафиксирована ошибка: %s", self.agent_id, exc)

    def mark_explained(self, explained: bool = True) -> None:
        self.metrics.explained.append(explained)

    def record_outcome(self, predicted_proba: float, actual_outcome: int) -> None:
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


PARSER_AGENT = TrackedAgent(
    agent_id="prizolov-parser-agent",
    domain="data-collection",
    autonomy="autonomous",
)

FORECAST_AGENT = TrackedAgent(
    agent_id="prizolov-forecast-agent",
    domain="sports-forecasting",
    autonomy="advisory",
)

router = APIRouter(tags=["agenomics"])


def _check_secret(x_api_secret: Optional[str], expected: Optional[str]) -> None:
    if not expected or x_api_secret != expected:
        raise HTTPException(status_code=403, detail="Invalid or missing X-Api-Secret")


@router.get("/trust")
def get_trust_scores(x_api_secret: str = Header(default=None)):
    _check_secret(x_api_secret, settings.api_secret)

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
        except Exception as exc:
            results[agent.agent_id] = {"error": str(exc)}

    return results