# Persistence for Elo, learning ledger, line opening snapshots.

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List

_lock = threading.Lock()
_PATH = Path(os.getenv("PREDICTION_STATE_PATH", "runtime/prediction_state.json"))


def _empty() -> Dict[str, Any]:
    return {
        "version": 1,
        "updated_at": None,
        "elo_ratings": {},  # team_name -> float
        "learning_ledger": [],
        "line_opening": {},  # event_key -> {line: opening_coef, ts}
        "clv_predictions": [],  # prediction-time vs pre-kickoff coef
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


def get_elo(team: str, default: float = 1500.0) -> float:
    state = load()
    ratings = state.get("elo_ratings") or {}
    return float(ratings.get(team.strip().lower(), default))


def set_elo(team: str, rating: float) -> None:
    state = load()
    ratings = dict(state.get("elo_ratings") or {})
    ratings[team.strip().lower()] = round(rating, 2)
    state["elo_ratings"] = ratings
    save(state)


def append_learning(record: Dict[str, Any], *, max_items: int = 3000) -> None:
    state = load()
    ledger = list(state.get("learning_ledger") or [])
    ledger.append(record)
    state["learning_ledger"] = ledger[-max_items:]
    save(state)


def append_clv_prediction(record: Dict[str, Any], *, max_items: int = 3000) -> None:
    state = load()
    items = list(state.get("clv_predictions") or [])
    items.append(record)
    state["clv_predictions"] = items[-max_items:]
    save(state)
