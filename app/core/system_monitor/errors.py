# Error tracking by category.

from __future__ import annotations

import threading
import time
from typing import Any, Dict

_lock = threading.Lock()
_counts: Dict[str, int] = {
    "api": 0,
    "parsing": 0,
    "prediction": 0,
    "database": 0,
    "other": 0,
}
_requests = 0


def record_error(category: str = "other") -> None:
    key = category if category in _counts else "other"
    with _lock:
        _counts[key] += 1


def record_request() -> None:
    global _requests
    with _lock:
        _requests += 1


def error_summary() -> Dict[str, Any]:
    with _lock:
        total_errors = sum(_counts.values())
        req = max(_requests, 1)
        return {
            "by_category": dict(_counts),
            "errors_total": total_errors,
            "requests_total": _requests,
            "error_rate_percent": round((total_errors / req) * 100.0, 3),
            "updated_at": time.time(),
        }
