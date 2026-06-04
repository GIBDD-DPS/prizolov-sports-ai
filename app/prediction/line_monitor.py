# Line movement: opening, current, delta over hours.

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from analytics.line_movement import event_key, push_line_snapshot
from prediction.store import load, save


def record_opening_if_absent(event: Dict[str, Any], bookmaker: str = "pari") -> None:
    state = load()
    openings: Dict[str, Any] = dict(state.get("line_opening") or {})
    ek = event_key(event)
    if ek in openings:
        return
    recs = event.get("recommendations") or event.get("all_recommendations") or []
    lines = {str(r.get("line")): float(r.get("coefficient") or 0) for r in recs if r.get("line")}
    if not lines:
        return
    openings[ek] = {"ts": time.time(), "bookmaker": bookmaker, "lines": lines}
    state["line_opening"] = openings
    save(state)
    push_line_snapshot(ek, bookmaker, [{"line": k, "coefficient": v} for k, v in lines.items()])


def line_movement_detail(event: Dict[str, Any]) -> Dict[str, Any]:
    state = load()
    ek = event_key(event)
    opening = (state.get("line_opening") or {}).get(ek)
    recs = event.get("recommendations") or event.get("all_recommendations") or []
    current = {str(r.get("line")): float(r.get("coefficient") or 0) for r in recs if r.get("line")}
    moves: List[Dict[str, Any]] = []
    if opening and opening.get("lines"):
        age_h = (time.time() - float(opening.get("ts") or time.time())) / 3600.0
        for line, open_coef in opening["lines"].items():
            cur = current.get(line)
            if not cur:
                continue
            delta = round(cur - float(open_coef), 3)
            if abs(delta) < 0.01:
                continue
            moves.append(
                {
                    "line": line,
                    "opening": round(float(open_coef), 3),
                    "current": round(cur, 3),
                    "delta": delta,
                    "hours_since_open": round(age_h, 2),
                    "signal": "steam" if delta < -0.05 else ("drift" if delta > 0.05 else "stable"),
                }
            )
    return {
        "event_key": ek,
        "opening_captured": bool(opening),
        "moves": moves,
        "tracked_lines": len(current),
    }
