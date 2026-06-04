# Pipeline stage latency tracking.

from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional

_lock = threading.Lock()
_last: Dict[str, float] = {}
_totals: Dict[str, float] = {}
_counts: Dict[str, int] = {}


@contextmanager
def track_stage(name: str) -> Generator[None, None, None]:
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        with _lock:
            _last[name] = elapsed
            _totals[name] = _totals.get(name, 0.0) + elapsed
            _counts[name] = _counts.get(name, 0) + 1


def record_stage(name: str, seconds: float) -> None:
    with _lock:
        _last[name] = seconds
        _totals[name] = _totals.get(name, 0.0) + seconds
        _counts[name] = _counts.get(name, 0) + 1


def snapshot() -> Dict[str, Any]:
    with _lock:
        stages = dict(_last)
    total = sum(stages.values())
    return {
        "data_collection": round(stages.get("data_collection", 0.0), 3),
        "feature_engineering": round(stages.get("feature_engineering", 0.0), 3),
        "ml_model": round(stages.get("ml_model", 0.0), 3),
        "llm_analysis": round(stages.get("llm_analysis", 0.0), 3),
        "total": round(total, 3),
        "last_stages": {k: round(v, 3) for k, v in stages.items()},
    }


def averages() -> Dict[str, float]:
    with _lock:
        out = {}
        for name, total in _totals.items():
            c = _counts.get(name) or 1
            out[name] = round(total / c, 3)
        return out
