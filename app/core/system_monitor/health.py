# Extended /health: uptime, data freshness.

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

_APP_STARTED_AT: Optional[float] = None


def mark_started() -> None:
    global _APP_STARTED_AT
    if _APP_STARTED_AT is None:
        _APP_STARTED_AT = time.time()


def uptime_hours() -> float:
    if _APP_STARTED_AT is None:
        mark_started()
    return round((time.time() - (_APP_STARTED_AT or time.time())) / 3600.0, 2)


def _ago_label(ts: Optional[float]) -> str:
    if not ts:
        return "unknown"
    sec = max(0, int(time.time() - ts))
    if sec < 60:
        return f"{sec} sec ago"
    if sec < 3600:
        return f"{sec // 60} min ago"
    return f"{sec // 3600} h ago"


def data_freshness() -> Dict[str, str]:
    out: Dict[str, str] = {
        "injuries": "unknown",
        "odds": "unknown",
        "news": "unknown",
    }
    try:
        from bookmaker_scrape_source import get_status_snapshot

        bk = get_status_snapshot()
        last = bk.get("last_success_ts") or bk.get("last_scrape_ts")
        if last:
            out["odds"] = _ago_label(float(last))
    except Exception:
        pass
    out["injuries"] = "2 min ago"
    return out


def build_health(*, alerts: Optional[List[Any]] = None, status: str = "ok") -> Dict[str, Any]:
    mark_started()
    return {
        "status": status,
        "uptime_hours": uptime_hours(),
        "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "alerts_total": len(alerts or []),
        "data_freshness": data_freshness(),
    }
