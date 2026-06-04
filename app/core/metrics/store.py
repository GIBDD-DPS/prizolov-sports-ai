# Unified metrics persistence (bets, Brier history, aggregates).

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List

_lock = threading.Lock()
_PATH = Path(os.getenv("METRICS_STATE_PATH", "runtime/metrics_state.json"))


def _empty() -> Dict[str, Any]:
    return {
        "version": 1,
        "updated_at": None,
        "bets": [],
        "brier_history": [],
        "totals": {
            "predictions": 0,
            "wins": 0,
            "losses": 0,
            "push": 0,
            "void": 0,
            "stake_total": 0.0,
            "profit_total": 0.0,
        },
    }


def load() -> Dict[str, Any]:
    with _lock:
        if not _PATH.exists():
            return _empty()
        try:
            data = json.loads(_PATH.read_text(encoding="utf-8"))
            base = _empty()
            if isinstance(data, dict):
                base.update(data)
            return base
        except (OSError, json.JSONDecodeError):
            return _empty()


def save(state: Dict[str, Any]) -> None:
    state["updated_at"] = time.time()
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        _PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def append_bet(record: Dict[str, Any], *, max_items: int = 5000) -> None:
    state = load()
    bets: List[Dict[str, Any]] = list(state.get("bets") or [])
    bets.append(record)
    state["bets"] = bets[-max_items:]
    save(state)


def append_brier(record: Dict[str, Any], *, max_items: int = 5000) -> None:
    state = load()
    hist: List[Dict[str, Any]] = list(state.get("brier_history") or [])
    hist.append(record)
    state["brier_history"] = hist[-max_items:]
    save(state)


def update_totals(**kwargs: Any) -> Dict[str, Any]:
    state = load()
    totals = dict(state.get("totals") or _empty()["totals"])
    for key, delta in kwargs.items():
        if key in totals:
            totals[key] = round(float(totals[key]) + float(delta), 4)
    state["totals"] = totals
    save(state)
    return totals
