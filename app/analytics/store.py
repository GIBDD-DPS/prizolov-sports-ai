# Persistent JSON store for analytics snapshots (CLV, ROI, line history).

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List

_lock = threading.Lock()
_DEFAULT_PATH = Path(os.getenv("ANALYTICS_STATE_PATH", "runtime/analytics_state.json"))


def _empty_state() -> Dict[str, Any]:
    return {
        "version": 1,
        "updated_at": None,
        "line_snapshots": {},  # event_key -> list[{ts, bookmaker, lines}]
        "clv_records": [],  # list of bet CLV entries
        "roi_ledger": [],  # virtual/real bet outcomes
        "xg_cache": {},  # event_key -> {xg_home, xga_home, ...}
    }


def load_state() -> Dict[str, Any]:
    path = _DEFAULT_PATH
    with _lock:
        if not path.exists():
            return _empty_state()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                base = _empty_state()
                base.update(data)
                return base
        except (OSError, json.JSONDecodeError):
            pass
        return _empty_state()


def save_state(state: Dict[str, Any]) -> None:
    path = _DEFAULT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = time.time()
    with _lock:
        path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def append_clv_record(record: Dict[str, Any], *, max_records: int = 5000) -> None:
    state = load_state()
    records: List[Dict[str, Any]] = list(state.get("clv_records") or [])
    records.append(record)
    state["clv_records"] = records[-max_records:]
    save_state(state)


def append_roi_entry(entry: Dict[str, Any], *, max_entries: int = 5000) -> None:
    state = load_state()
    ledger: List[Dict[str, Any]] = list(state.get("roi_ledger") or [])
    ledger.append(entry)
    state["roi_ledger"] = ledger[-max_entries:]
    save_state(state)


def push_line_snapshot(
    event_key: str,
    bookmaker: str,
    lines: List[Dict[str, Any]],
    *,
    max_snapshots_per_event: int = 120,
) -> None:
    state = load_state()
    snapshots: Dict[str, List[Dict[str, Any]]] = dict(state.get("line_snapshots") or {})
    bucket = list(snapshots.get(event_key) or [])
    bucket.append(
        {
            "ts": time.time(),
            "bookmaker": bookmaker,
            "lines": lines,
        }
    )
    snapshots[event_key] = bucket[-max_snapshots_per_event:]
    state["line_snapshots"] = snapshots
    save_state(state)


def set_xg_cache(event_key: str, payload: Dict[str, Any]) -> None:
    state = load_state()
    cache = dict(state.get("xg_cache") or {})
    cache[event_key] = payload
    state["xg_cache"] = cache
    save_state(state)
