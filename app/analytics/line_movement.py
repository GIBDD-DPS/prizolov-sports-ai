# Line movement monitor: PARI (scrape) + Pinnacle (API feed).

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

from analytics.store import load_state, push_line_snapshot


def event_key(event: Dict[str, Any]) -> str:
    return "|".join(
        [
            str(event.get("home") or ""),
            str(event.get("away") or ""),
            str(event.get("sport") or ""),
            str(event.get("league") or ""),
        ]
    )


def record_pari_lines_from_event(event: Dict[str, Any]) -> None:
    recs = event.get("recommendations") or event.get("all_recommendations") or []
    lines = [
        {
            "line": r.get("line"),
            "coefficient": r.get("coefficient"),
            "probability": r.get("probability"),
        }
        for r in recs
        if r.get("line") and r.get("coefficient")
    ]
    if not lines:
        return
    push_line_snapshot(event_key(event), "pari", lines)


def record_pinnacle_lines_from_event(event: Dict[str, Any]) -> None:
    """Optional: events pre-tagged with bookmaker=pinnacle or odds_source."""
    if str(event.get("odds_source") or "").lower() != "pinnacle":
        return
    recs = event.get("recommendations") or []
    lines = [
        {"line": r.get("line"), "coefficient": r.get("coefficient")}
        for r in recs
        if r.get("coefficient")
    ]
    if lines:
        push_line_snapshot(event_key(event), "pinnacle", lines)


def _movement_for_snapshots(snapshots: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if len(snapshots) < 2:
        return None
    prev = snapshots[-2]
    curr = snapshots[-1]
    prev_map = {l["line"]: float(l["coefficient"]) for l in prev.get("lines") or [] if l.get("line")}
    curr_map = {l["line"]: float(l["coefficient"]) for l in curr.get("lines") or [] if l.get("line")}
    moves = []
    for line, coef_now in curr_map.items():
        coef_was = prev_map.get(line)
        if coef_was is None:
            continue
        delta = coef_now - coef_was
        if abs(delta) < 0.01:
            continue
        moves.append(
            {
                "line": line,
                "from": round(coef_was, 3),
                "to": round(coef_now, 3),
                "delta": round(delta, 3),
                "direction": "shortened" if delta < 0 else "drifted",
            }
        )
    if not moves:
        return None
    return {
        "bookmaker": curr.get("bookmaker"),
        "age_seconds": int(time.time() - float(prev.get("ts") or time.time())),
        "moves": moves,
    }


def line_movement_report(*, min_moves: int = 1, limit: int = 50) -> List[Dict[str, Any]]:
    state = load_state()
    snapshots: Dict[str, List[Dict[str, Any]]] = dict(state.get("line_snapshots") or {})
    report: List[Dict[str, Any]] = []
    for ek, hist in snapshots.items():
        pari_hist = [h for h in hist if h.get("bookmaker") == "pari"]
        pin_hist = [h for h in hist if h.get("bookmaker") == "pinnacle"]
        pari_move = _movement_for_snapshots(pari_hist)
        pin_move = _movement_for_snapshots(pin_hist)
        if not pari_move and not pin_move:
            continue
        move_count = len((pari_move or {}).get("moves") or []) + len((pin_move or {}).get("moves") or [])
        if move_count < min_moves:
            continue
        report.append(
            {
                "event_key": ek,
                "pari": pari_move,
                "pinnacle": pin_move,
            }
        )
    return report[:limit]


def ingest_pinnacle_feed(events: List[Dict[str, Any]]) -> int:
    """Hook for Odds API / Pinnacle-normalized events."""
    count = 0
    for event in events:
        if "pinnacle" in str(event.get("source_url") or "").lower() or event.get("bookmaker") == "pinnacle":
            event = dict(event)
            event["odds_source"] = "pinnacle"
            record_pinnacle_lines_from_event(event)
            count += 1
    return count


def line_monitor_status() -> Dict[str, Any]:
    state = load_state()
    snapshots = state.get("line_snapshots") or {}
    pari_events = sum(1 for h in snapshots.values() if any(s.get("bookmaker") == "pari" for s in h))
    pin_events = sum(1 for h in snapshots.values() if any(s.get("bookmaker") == "pinnacle" for s in h))
    return {
        "pari_tracked_events": pari_events,
        "pinnacle_tracked_events": pin_events,
        "pinnacle_feed_enabled": bool(os.getenv("PINNACLE_ODDS_ENABLED", "").lower() in {"1", "true", "yes"}),
        "snapshot_events_total": len(snapshots),
    }
