# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.0 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

import copy
import datetime
import hashlib
import json
import logging
import os
import pathlib
import random
import sys
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("PrizolovSportsAI.Main")

# Гарантируем, что текущая папка (app/) находится в системных путях
current_dir = pathlib.Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Инициализация приложения FastAPI
app = FastAPI(title="Prizolov Sports AI", version="14.0")

# Глобальный CORS для связи с prizolov.ru
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# КОНФИГ
# ============================================

CACHE_TTL_SECONDS = int(os.getenv("STORE_CACHE_TTL_SECONDS", "30"))
LOW_EVENT_ALERT_THRESHOLD = int(os.getenv("LOW_EVENT_ALERT_THRESHOLD", "4"))
LOW_EVENT_STREAK_ALERT = int(os.getenv("LOW_EVENT_STREAK_ALERT", "3"))

DEFAULT_WINDOW_HOURS = int(os.getenv("DEFAULT_WINDOW_HOURS", "24"))
DEFAULT_MIN_PROBABILITY = float(os.getenv("DEFAULT_MIN_PROBABILITY", "0.6"))
DEFAULT_MIN_COEFFICIENT = float(os.getenv("DEFAULT_MIN_COEFFICIENT", "1.5"))
DEFAULT_MIN_BOOKMAKERS_SUPPORT = float(os.getenv("DEFAULT_MIN_BOOKMAKERS_SUPPORT", "2.0"))

MAX_ODDS_AGE_SECONDS = int(os.getenv("MAX_ODDS_AGE_SECONDS", "900"))  # 15 минут
STALE_ODDS_PENALTY_FACTOR = float(os.getenv("STALE_ODDS_PENALTY_FACTOR", "0.92"))


# ============================================
# ДАННЫЕ (LIVE + UPCOMING)
# ============================================

LIVE_EVENTS = [
    {
        "id": "f1",
        "sport": "football",
        "league": "РПЛ",
        "home": "Зенит",
        "away": "Спартак",
        "status": "LIVE",
        "time": "67'",
        "score": "2-1",
        "recommendations": [
            {"line": "Тотал больше 2.5", "coefficient": 1.85, "probability": 0.82, "confidence": "high"},
            {"line": "Обе забьют - ДА", "coefficient": 1.72, "probability": 0.78, "confidence": "high"},
            {"line": "Победа 1", "coefficient": 1.65, "probability": 0.71, "confidence": "med"},
        ],
    },
    {
        "id": "f2",
        "sport": "football",
        "league": "La Liga",
        "home": "Barcelona",
        "away": "Real Madrid",
        "status": "LIVE",
        "time": "45'",
        "score": "1-1",
        "recommendations": [
            {"line": "Тотал больше 2.5", "coefficient": 1.92, "probability": 0.79, "confidence": "high"},
            {"line": "Обе забьют - ДА", "coefficient": 1.88, "probability": 0.74, "confidence": "high"},
            {"line": "Фора 0(-1)", "coefficient": 2.10, "probability": 0.65, "confidence": "med"},
        ],
    },
    {
        "id": "h1",
        "sport": "hockey",
        "league": "КХЛ",
        "home": "ЦСКА",
        "away": "Динамо",
        "status": "LIVE",
        "time": "2:15",
        "score": "3-2",
        "recommendations": [
            {"line": "Тотал больше 5.5", "coefficient": 1.82, "probability": 0.80, "confidence": "high"},
            {"line": "Обе забьют - ДА", "coefficient": 1.65, "probability": 0.85, "confidence": "high"},
        ],
    },
    {
        "id": "b1",
        "sport": "basketball",
        "league": "NBA",
        "home": "Los Angeles Lakers",
        "away": "Boston Celtics",
        "status": "LIVE",
        "time": "2 четверть",
        "score": "45-38",
        "recommendations": [
            {"line": "Тотал больше 210.5", "coefficient": 1.88, "probability": 0.77, "confidence": "high"},
            {"line": "Победа 1", "coefficient": 1.95, "probability": 0.69, "confidence": "med"},
        ],
    },
    {
        "id": "t1",
        "sport": "tennis",
        "league": "ATP",
        "home": "Novak Djokovic",
        "away": "Jannik Sinner",
        "status": "LIVE",
        "time": "2 сет 4:2",
        "score": "1-1",
        "recommendations": [
            {"line": "Геймы 2 сета больше 8.5", "coefficient": 1.88, "probability": 0.76, "confidence": "high"},
            {"line": "Победа 1", "coefficient": 2.05, "probability": 0.62, "confidence": "med"},
        ],
    },
    {
        "id": "e1",
        "sport": "esports",
        "league": "CS2 Pro League",
        "home": "FaZe Clan",
        "away": "NAVI",
        "status": "LIVE",
        "time": "Map 2 - 8:7",
        "score": "1-0",
        "recommendations": [
            {"line": "Победа 1", "coefficient": 1.78, "probability": 0.70, "confidence": "med"},
            {"line": "Матч пойдет на 3-ю карту", "coefficient": 2.10, "probability": 0.65, "confidence": "high"},
        ],
    },
]

UPCOMING_EVENT_TEMPLATES = [
    ("u1", "football", "Bundesliga", "Bayern Munich", "Borussia Dortmund", 1.0, [
        {"line": "Тотал больше 2.5", "coefficient": 1.76, "probability": 0.74, "confidence": "high"},
        {"line": "Обе забьют - ДА", "coefficient": 1.70, "probability": 0.77, "confidence": "high"},
    ]),
    ("u2", "football", "Ligue 1", "PSG", "Marseille", 2.5, [
        {"line": "Победа 1", "coefficient": 1.66, "probability": 0.75, "confidence": "high"},
        {"line": "Тотал больше 2.5", "coefficient": 1.83, "probability": 0.72, "confidence": "med"},
    ]),
    ("u3", "hockey", "NHL", "Edmonton Oilers", "Colorado Avalanche", 3.0, [
        {"line": "Тотал больше 5.5", "coefficient": 1.90, "probability": 0.72, "confidence": "high"},
        {"line": "Обе забьют - ДА", "coefficient": 1.62, "probability": 0.82, "confidence": "high"},
    ]),
    ("u4", "basketball", "NBA", "Phoenix Suns", "Denver Nuggets", 4.0, [
        {"line": "Тотал больше 221.5", "coefficient": 1.98, "probability": 0.69, "confidence": "high"},
        {"line": "Фора 1 (+4.5)", "coefficient": 1.72, "probability": 0.73, "confidence": "med"},
    ]),
    ("u5", "tennis", "ATP", "Carlos Alcaraz", "Daniil Medvedev", 5.0, [
        {"line": "Тотал геймов больше 22.5", "coefficient": 1.91, "probability": 0.70, "confidence": "high"},
        {"line": "Победа 1", "coefficient": 1.83, "probability": 0.67, "confidence": "med"},
    ]),
    ("u6", "volleyball", "FIVB Nations League", "Brazil", "Italy", 6.0, [
        {"line": "Тотал сетов больше 3.5", "coefficient": 1.68, "probability": 0.79, "confidence": "high"},
        {"line": "Победа 2", "coefficient": 2.08, "probability": 0.61, "confidence": "med"},
    ]),
    ("u7", "handball", "EHF Champions League", "Kiel", "Veszprem", 7.0, [
        {"line": "Тотал больше 56.5", "coefficient": 1.88, "probability": 0.72, "confidence": "high"},
        {"line": "Обе забьют более 27", "coefficient": 1.66, "probability": 0.78, "confidence": "high"},
    ]),
    ("u8", "esports", "CS2 Major", "G2", "Vitality", 8.5, [
        {"line": "Матч пойдет на 3-ю карту", "coefficient": 2.04, "probability": 0.64, "confidence": "high"},
        {"line": "Победа 1", "coefficient": 1.84, "probability": 0.66, "confidence": "med"},
    ]),
    ("u9", "mma", "UFC Fight Night", "Fighter A", "Fighter B", 10.0, [
        {"line": "Победа 1", "coefficient": 1.95, "probability": 0.65, "confidence": "med"},
        {"line": "Бой продлится 3 раунда", "coefficient": 1.74, "probability": 0.71, "confidence": "high"},
    ]),
    ("u10", "baseball", "MLB", "Yankees", "Dodgers", 11.0, [
        {"line": "Тотал больше 8.5", "coefficient": 1.86, "probability": 0.70, "confidence": "high"},
        {"line": "Победа 2", "coefficient": 2.02, "probability": 0.62, "confidence": "med"},
    ]),
    ("u11", "american_football", "NFL", "Chiefs", "Bills", 12.0, [
        {"line": "Тотал больше 48.5", "coefficient": 1.92, "probability": 0.69, "confidence": "high"},
        {"line": "Фора 1 (-2.5)", "coefficient": 1.78, "probability": 0.67, "confidence": "med"},
    ]),
    ("u12", "rugby", "Super Rugby", "Crusaders", "Blues", 13.0, [
        {"line": "Тотал больше 43.5", "coefficient": 1.84, "probability": 0.72, "confidence": "high"},
        {"line": "Победа 1", "coefficient": 1.88, "probability": 0.66, "confidence": "med"},
    ]),
    ("u13", "cricket", "T20 League", "Mumbai", "Chennai", 15.0, [
        {"line": "Тотал ранов больше 168.5", "coefficient": 1.80, "probability": 0.73, "confidence": "high"},
        {"line": "Победа 2", "coefficient": 2.15, "probability": 0.60, "confidence": "med"},
    ]),
    ("u14", "futsal", "UEFA Futsal Cup", "Sporting", "Benfica", 18.0, [
        {"line": "Тотал больше 5.5", "coefficient": 1.86, "probability": 0.71, "confidence": "high"},
        {"line": "Обе забьют - ДА", "coefficient": 1.58, "probability": 0.83, "confidence": "high"},
    ]),
    ("u15", "table_tennis", "WTT", "Fan Zhendong", "Ma Long", 20.0, [
        {"line": "Тотал сетов больше 4.5", "coefficient": 1.93, "probability": 0.67, "confidence": "high"},
        {"line": "Победа 1", "coefficient": 1.70, "probability": 0.74, "confidence": "med"},
    ]),
    ("u16", "badminton", "BWF World Tour", "Axelsen", "Kodai Naraoka", 22.0, [
        {"line": "Тотал очков больше 74.5", "coefficient": 1.82, "probability": 0.70, "confidence": "high"},
        {"line": "Победа 1", "coefficient": 1.62, "probability": 0.78, "confidence": "high"},
    ]),
]


# ============================================
# ВНУТРЕННЕЕ СОСТОЯНИЕ
# ============================================

_cache_lock = threading.Lock()
_cache: Dict[str, Dict[str, Any]] = {}

_metrics_lock = threading.Lock()
_metrics: Dict[str, Any] = {
    "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "requests_total": 0,
    "errors_total": 0,
    "cache_hits": 0,
    "cache_misses": 0,
    "fallback_usage": {
        "legacy_get_all": 0,
        "event_index_mode": 0,
    },
    "endpoints": {},
}

_runtime_state: Dict[str, Any] = {
    "low_event_streak": 0,
    "last_storefront_total": 0,
    "last_storefront_generated_at": None,
    "last_alerts": [],
}


# ============================================
# HELPER
# ============================================

def _now_utc() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _safe_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _coerce_int(value: Any, default: int, minimum: Optional[int] = None, maximum: Optional[int] = None) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    if minimum is not None:
        parsed = max(minimum, parsed)
    if maximum is not None:
        parsed = min(maximum, parsed)
    return parsed


def _coerce_float(value: Any, default: float, minimum: Optional[float] = None, maximum: Optional[float] = None) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    if minimum is not None:
        parsed = max(minimum, parsed)
    if maximum is not None:
        parsed = min(maximum, parsed)
    return parsed


def _deterministic_int(seed: str, low: int, high: int) -> int:
    if high <= low:
        return low
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    value = int(digest[:8], 16)
    return low + (value % (high - low + 1))


def _parse_iso_datetime(value: Any) -> Optional[datetime.datetime]:
    if not value:
        return None
    try:
        dt = datetime.datetime.fromisoformat(str(value))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt.astimezone(datetime.timezone.utc)
    except Exception:
        return None


def _json_dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _cache_key(prefix: str, params: Dict[str, Any]) -> str:
    return f"{prefix}:{_json_dumps(params)}"


def _make_etag(payload: Dict[str, Any]) -> str:
    digest = hashlib.sha256(_json_dumps(payload).encode("utf-8")).hexdigest()
    return f'W/"{digest}"'


def _record_endpoint_metric(path: str, elapsed_ms: float, status_code: int) -> None:
    now_iso = _now_utc().isoformat()
    with _metrics_lock:
        _metrics["requests_total"] += 1
        if status_code >= 500:
            _metrics["errors_total"] += 1

        endpoint = _metrics["endpoints"].setdefault(
            path,
            {
                "count": 0,
                "errors": 0,
                "total_latency_ms": 0.0,
                "avg_latency_ms": 0.0,
                "last_status": None,
                "last_seen": None,
            },
        )
        endpoint["count"] += 1
        endpoint["total_latency_ms"] += elapsed_ms
        endpoint["avg_latency_ms"] = round(endpoint["total_latency_ms"] / endpoint["count"], 2)
        endpoint["last_status"] = status_code
        endpoint["last_seen"] = now_iso
        if status_code >= 500:
            endpoint["errors"] += 1


def _cache_get(key: str) -> Optional[Dict[str, Any]]:
    with _cache_lock:
        entry = _cache.get(key)
        now_ts = time.time()
        if entry and entry["expires_at"] > now_ts:
            with _metrics_lock:
                _metrics["cache_hits"] += 1
            return entry
        if entry:
            _cache.pop(key, None)
        with _metrics_lock:
            _metrics["cache_misses"] += 1
        return None


def _cache_put(key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    now = _now_utc()
    entry = {
        "payload": payload,
        "etag": _make_etag(payload),
        "last_modified": now.strftime("%a, %d %b %Y %H:%M:%S GMT"),
        "cached_at": now.isoformat(),
        "expires_at": time.time() + CACHE_TTL_SECONDS,
    }
    with _cache_lock:
        _cache[key] = entry
    return entry


def _update_low_event_streak(events_total: int) -> None:
    with _metrics_lock:
        if events_total < LOW_EVENT_ALERT_THRESHOLD:
            _runtime_state["low_event_streak"] += 1
        else:
            _runtime_state["low_event_streak"] = 0
        _runtime_state["last_storefront_total"] = events_total
        _runtime_state["last_storefront_generated_at"] = _now_utc().isoformat()


def _build_alerts() -> List[Dict[str, Any]]:
    alerts: List[Dict[str, Any]] = []
    with _metrics_lock:
        low_streak = _runtime_state["low_event_streak"]
        last_total = _runtime_state["last_storefront_total"]
        req_total = _metrics["requests_total"]
        err_total = _metrics["errors_total"]
        err_rate = (err_total / req_total) if req_total > 0 else 0.0

        if low_streak >= LOW_EVENT_STREAK_ALERT:
            alerts.append(
                {
                    "level": "critical",
                    "code": "low_events_streak",
                    "message": f"Низкое число событий подряд: {low_streak} циклов (последнее значение: {last_total}).",
                }
            )
        elif last_total < LOW_EVENT_ALERT_THRESHOLD:
            alerts.append(
                {
                    "level": "warning",
                    "code": "low_events_snapshot",
                    "message": f"Мало событий в витрине: {last_total} (< {LOW_EVENT_ALERT_THRESHOLD}).",
                }
            )

        if err_rate >= 0.10:
            alerts.append(
                {
                    "level": "warning",
                    "code": "high_error_rate",
                    "message": f"Повышенный error-rate API: {round(err_rate * 100, 2)}%.",
                }
            )

        cache_hits = _metrics["cache_hits"]
        cache_misses = _metrics["cache_misses"]
        total_cache_checks = cache_hits + cache_misses
        cache_ratio = (cache_hits / total_cache_checks) if total_cache_checks else 0.0
        if total_cache_checks > 10 and cache_ratio < 0.2:
            alerts.append(
                {
                    "level": "info",
                    "code": "low_cache_hit_ratio",
                    "message": f"Низкий cache hit ratio: {round(cache_ratio * 100, 2)}%.",
                }
            )

        _runtime_state["last_alerts"] = alerts
    return alerts


async def _read_payload(request: Request) -> Dict[str, Any]:
    try:
        data = await request.json()
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


# ============================================
# ПОСТРОЕНИЕ ДАННЫХ
# ============================================

def _build_live_events(now_utc: datetime.datetime) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    for raw in LIVE_EVENTS:
        event = copy.deepcopy(raw)
        seed = event["id"]
        live_minutes = _deterministic_int(seed + ":live-minutes", 5, 95)
        start_at = now_utc - datetime.timedelta(minutes=live_minutes)
        event["is_live"] = True
        event["start_at"] = start_at.isoformat()

        for rec in event.get("recommendations", []):
            rec_seed = f"{seed}:{rec.get('line', '')}"
            rec["bookmakers_support"] = float(_deterministic_int(rec_seed + ":support", 1, 6))
            odds_age = _deterministic_int(rec_seed + ":odds-age", 1, 30)
            rec["odds_updated_at"] = (now_utc - datetime.timedelta(minutes=odds_age)).isoformat()
        events.append(event)
    return events


def _build_upcoming_events(now_utc: datetime.datetime, window_hours: int) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    horizon = now_utc + datetime.timedelta(hours=window_hours)
    for tpl in UPCOMING_EVENT_TEMPLATES:
        event_id, sport, league, home, away, offset_h, recs = tpl
        start_at = now_utc + datetime.timedelta(hours=float(offset_h))
        if start_at > horizon:
            continue

        event = {
            "id": event_id,
            "sport": sport,
            "league": league,
            "home": home,
            "away": away,
            "status": "UPCOMING",
            "time": start_at.strftime("%d.%m %H:%M UTC"),
            "score": "—",
            "is_live": False,
            "start_at": start_at.isoformat(),
            "recommendations": copy.deepcopy(recs),
        }
        for rec in event["recommendations"]:
            rec_seed = f"{event_id}:{rec.get('line', '')}"
            rec["bookmakers_support"] = float(_deterministic_int(rec_seed + ":support", 1, 7))
            odds_age = _deterministic_int(rec_seed + ":odds-age", 1, 45)
            rec["odds_updated_at"] = (now_utc - datetime.timedelta(minutes=odds_age)).isoformat()
        events.append(event)
    return events


def _collect_raw_events(window_hours: int, include_live: bool, include_upcoming: bool) -> List[Dict[str, Any]]:
    now_utc = _now_utc()
    items: List[Dict[str, Any]] = []
    if include_live:
        items.extend(_build_live_events(now_utc))
    if include_upcoming:
        items.extend(_build_upcoming_events(now_utc, window_hours))
    return items


def _score_recommendation(rec: Dict[str, Any], now_utc: datetime.datetime) -> Dict[str, Any]:
    probability = _coerce_float(rec.get("probability"), 0.0, minimum=0.0, maximum=1.0)
    coefficient = _coerce_float(rec.get("coefficient"), 1.5, minimum=1.01, maximum=50.0)
    support = _coerce_float(rec.get("bookmakers_support"), 1.0, minimum=0.0, maximum=15.0)

    odds_updated = _parse_iso_datetime(rec.get("odds_updated_at"))
    if odds_updated is None:
        odds_updated = now_utc
    age_seconds = max(0, int((now_utc - odds_updated).total_seconds()))
    is_stale = age_seconds > MAX_ODDS_AGE_SECONDS

    adjusted_probability = probability * (STALE_ODDS_PENALTY_FACTOR if is_stale else 1.0)
    implied_probability = min(1.0, 1.0 / coefficient)
    edge = adjusted_probability - implied_probability

    quality_score = (
        adjusted_probability * 0.72
        + min(coefficient / 3.0, 1.0) * 0.12
        + min(support / 6.0, 1.0) * 0.16
    )
    if is_stale:
        quality_score *= 0.90

    enriched = copy.deepcopy(rec)
    enriched["probability"] = round(probability, 4)
    enriched["adjusted_probability"] = round(adjusted_probability, 4)
    enriched["coefficient"] = round(coefficient, 2)
    enriched["bookmakers_support"] = round(support, 2)
    enriched["implied_probability"] = round(implied_probability, 4)
    enriched["edge"] = round(edge, 4)
    enriched["quality_score"] = round(quality_score, 4)
    enriched["odds_age_seconds"] = age_seconds
    enriched["is_stale_odds"] = is_stale
    enriched["recommendation_type"] = "passable" if edge > 0 else "watch"
    return enriched


def _prepare_event(
    raw_event: Dict[str, Any],
    min_probability: float,
    min_coefficient: float,
    min_support: float,
) -> Dict[str, Any]:
    now_utc = _now_utc()
    scored = [_score_recommendation(rec, now_utc) for rec in raw_event.get("recommendations", [])]
    scored.sort(key=lambda r: (-r["adjusted_probability"], -r["coefficient"], -r["quality_score"]))

    passable = [
        rec
        for rec in scored
        if rec["adjusted_probability"] > min_probability
        and rec["coefficient"] >= min_coefficient
        and rec["bookmakers_support"] >= min_support
    ]
    watch = [rec for rec in scored if rec not in passable]

    event = copy.deepcopy(raw_event)
    event["all_recommendations"] = scored
    event["passable_recommendations"] = passable
    event["watch_recommendations"] = watch
    event["recommendations"] = scored  # backwards-compatible field
    event["top_probability_passable"] = passable[0]["adjusted_probability"] if passable else 0.0
    event["top_probability_any"] = scored[0]["adjusted_probability"] if scored else 0.0
    event["top_recommendation_quality"] = scored[0]["quality_score"] if scored else 0.0
    event["has_passable"] = bool(passable)
    return event


def _build_sports_map(events: List[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    sports: Dict[str, Dict[str, int]] = {}
    for event in events:
        sport = event.get("sport", "unknown")
        item = sports.setdefault(sport, {"events_total": 0, "events_with_passable": 0, "passable_recommendations": 0})
        item["events_total"] += 1
        passable = event.get("passable_recommendations", [])
        if passable:
            item["events_with_passable"] += 1
        item["passable_recommendations"] += len(passable)
    return sports


def _sports_line(sports_map: Dict[str, Dict[str, int]]) -> List[str]:
    ordered = sorted(
        sports_map.items(),
        key=lambda item: (-item[1]["events_with_passable"], -item[1]["events_total"], item[0]),
    )
    return [name for name, _ in ordered]


def _sort_events(events: List[Dict[str, Any]], sort_by: str) -> None:
    if sort_by == "time":
        events.sort(key=lambda e: e.get("start_at", ""))
        return

    events.sort(
        key=lambda e: (
            -_coerce_float(e.get("top_probability_passable"), 0.0),
            -_coerce_float(e.get("top_probability_any"), 0.0),
            e.get("start_at", ""),
        )
    )


def _build_storefront_payload(
    *,
    window_hours: int,
    include_live: bool,
    include_upcoming: bool,
    min_probability: float,
    min_coefficient: float,
    min_support: float,
    recommendations_only: bool,
    include_watch: bool,
    sort_by: str,
    limit: int,
    offset: int,
) -> Dict[str, Any]:
    raw_events = _collect_raw_events(window_hours, include_live, include_upcoming)
    prepared = [_prepare_event(e, min_probability, min_coefficient, min_support) for e in raw_events]

    if recommendations_only:
        prepared = [e for e in prepared if e.get("has_passable")]

    _sort_events(prepared, sort_by)

    total_before_pagination = len(prepared)
    if offset > 0:
        prepared = prepared[offset:]
    if limit > 0:
        prepared = prepared[:limit]

    for event in prepared:
        if include_watch:
            event["recommendations"] = event.get("all_recommendations", [])
        else:
            event["recommendations"] = event.get("passable_recommendations", [])

    sports_map = _build_sports_map(prepared)
    sports_line = _sports_line(sports_map)

    passable_recommendations_total = sum(len(e.get("passable_recommendations", [])) for e in prepared)
    avg_coef = 0.0
    if passable_recommendations_total > 0:
        coef_sum = sum(
            rec.get("coefficient", 0.0)
            for e in prepared
            for rec in e.get("passable_recommendations", [])
        )
        avg_coef = round(coef_sum / passable_recommendations_total, 3)

    payload = {
        "total": len(prepared),
        "events": prepared,
        "window_hours": window_hours,
        "sports": sports_map,
        "sports_line": sports_line,
        "filters": {
            "include_live": include_live,
            "include_upcoming": include_upcoming,
            "min_probability": min_probability,
            "min_coefficient": min_coefficient,
            "min_bookmakers_support": min_support,
            "recommendations_only": recommendations_only,
            "include_watch": include_watch,
            "sort_by": sort_by,
            "limit": limit,
            "offset": offset,
        },
        "stats": {
            "events_total_before_pagination": total_before_pagination,
            "events_total": len(prepared),
            "sports_total": len(sports_line),
            "passable_recommendations_total": passable_recommendations_total,
            "average_passable_coefficient": avg_coef,
        },
        "generated_at": _now_utc().isoformat(),
        "source": "storefront-aggregated",
    }

    _update_low_event_streak(len(prepared))
    return payload


def _storefront_cache_entry(params: Dict[str, Any], refresh: bool = False) -> Dict[str, Any]:
    key = _cache_key("storefront", params)
    if not refresh:
        cached = _cache_get(key)
        if cached is not None:
            return cached

    payload = _build_storefront_payload(**params)
    return _cache_put(key, payload)


def _state_payload_from_event(event: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
    display_recs = event.get("passable_recommendations") or event.get("all_recommendations") or []
    recommendations = [
        {
            "league": event.get("league"),
            "sport": event.get("sport"),
            "home": event.get("home"),
            "away": event.get("away"),
            "line": rec.get("line"),
            "confidence": rec.get("confidence", "med"),
            "probability": rec.get("adjusted_probability", rec.get("probability", 0.0)),
            "coefficient": rec.get("coefficient"),
            "bookmakers_support": rec.get("bookmakers_support"),
            "edge": rec.get("edge"),
            "quality_score": rec.get("quality_score"),
            "is_stale_odds": rec.get("is_stale_odds"),
        }
        for rec in display_recs
    ]

    score = event.get("score", "—")
    status = event.get("time", "—")
    if event.get("is_live"):
        status = f"{status} ({score})"

    return {
        "match_info": {
            "league": event.get("league"),
            "home": event.get("home"),
            "away": event.get("away"),
            "status": status,
            "sport": event.get("sport"),
            "start_at": event.get("start_at"),
            "is_live": event.get("is_live", False),
        },
        "recommendations": recommendations,
        "meta": meta,
    }


def _increment_fallback_usage(key: str) -> None:
    with _metrics_lock:
        bucket = _metrics["fallback_usage"]
        bucket[key] = bucket.get(key, 0) + 1


# ============================================
# MIDDLEWARE
# ============================================

@app.middleware("http")
async def _metrics_middleware(request: Request, call_next):
    started = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
    except Exception:
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        _record_endpoint_metric(request.url.path, elapsed_ms, status)
        raise

    elapsed_ms = (time.perf_counter() - started) * 1000.0
    _record_endpoint_metric(request.url.path, elapsed_ms, status)
    response.headers.setdefault("X-Process-Time-Ms", str(round(elapsed_ms, 2)))
    return response


# ============================================
# API
# ============================================

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 PRIZOLOV SPORTS AI v14.0 - STORE-FRONT OPTIMIZED")
    logger.info(f"📦 Storefront cache TTL: {CACHE_TTL_SECONDS}s")


@app.get("/")
async def root():
    alerts = _build_alerts()
    return {
        "status": "online",
        "version": "14.0",
        "mode": "storefront-optimized",
        "alerts": alerts,
    }


@app.get("/health")
async def health():
    alerts = _build_alerts()
    return {
        "status": "ok",
        "timestamp": _now_utc().isoformat(),
        "alerts_total": len(alerts),
    }


@app.get("/api/all-events")
async def get_all_events(
    request: Request,
    window_hours: int = DEFAULT_WINDOW_HOURS,
    include_live: bool = True,
    include_upcoming: bool = True,
    min_probability: float = DEFAULT_MIN_PROBABILITY,
    min_coefficient: float = DEFAULT_MIN_COEFFICIENT,
    min_bookmakers_support: float = DEFAULT_MIN_BOOKMAKERS_SUPPORT,
    recommendations_only: bool = False,
    passable_only: Optional[bool] = None,
    include_watch: bool = True,
    sort_by: str = "passability",
    limit: int = 120,
    offset: int = 0,
    refresh: bool = False,
):
    normalized_window = _coerce_int(window_hours, DEFAULT_WINDOW_HOURS, minimum=1, maximum=72)
    normalized_min_probability = _coerce_float(min_probability, DEFAULT_MIN_PROBABILITY, minimum=0.0, maximum=1.0)
    normalized_min_coef = _coerce_float(min_coefficient, DEFAULT_MIN_COEFFICIENT, minimum=1.0, maximum=50.0)
    normalized_min_support = _coerce_float(min_bookmakers_support, DEFAULT_MIN_BOOKMAKERS_SUPPORT, minimum=0.0, maximum=20.0)
    normalized_limit = _coerce_int(limit, 120, minimum=1, maximum=500)
    normalized_offset = _coerce_int(offset, 0, minimum=0, maximum=5000)

    recommendations_only_final = _safe_bool(passable_only, _safe_bool(recommendations_only, False))
    include_watch_final = _safe_bool(include_watch, True)
    sort_key = "time" if str(sort_by).lower() == "time" else "passability"

    params = {
        "window_hours": normalized_window,
        "include_live": _safe_bool(include_live, True),
        "include_upcoming": _safe_bool(include_upcoming, True),
        "min_probability": normalized_min_probability,
        "min_coefficient": normalized_min_coef,
        "min_support": normalized_min_support,
        "recommendations_only": recommendations_only_final,
        "include_watch": include_watch_final,
        "sort_by": sort_key,
        "limit": normalized_limit,
        "offset": normalized_offset,
    }

    entry = _storefront_cache_entry(params, refresh=_safe_bool(refresh, False))

    if_none_match = request.headers.get("if-none-match")
    if if_none_match and if_none_match == entry["etag"]:
        return Response(
            status_code=304,
            headers={
                "ETag": entry["etag"],
                "Last-Modified": entry["last_modified"],
                "Cache-Control": f"public, max-age={CACHE_TTL_SECONDS}",
            },
        )

    return JSONResponse(
        content=entry["payload"],
        headers={
            "ETag": entry["etag"],
            "Last-Modified": entry["last_modified"],
            "Cache-Control": f"public, max-age={CACHE_TTL_SECONDS}",
            "X-Storefront-Cache": "HIT" if entry["expires_at"] > time.time() else "MISS",
        },
    )


@app.post("/api/state")
async def get_state(request: Request):
    payload = await _read_payload(request)
    params = {
        "window_hours": _coerce_int(payload.get("window_hours"), DEFAULT_WINDOW_HOURS, minimum=1, maximum=72),
        "include_live": _safe_bool(payload.get("include_live"), True),
        "include_upcoming": _safe_bool(payload.get("include_upcoming"), True),
        "min_probability": _coerce_float(payload.get("min_probability"), DEFAULT_MIN_PROBABILITY, minimum=0.0, maximum=1.0),
        "min_coefficient": _coerce_float(payload.get("min_coefficient"), DEFAULT_MIN_COEFFICIENT, minimum=1.0, maximum=50.0),
        "min_support": _coerce_float(payload.get("min_bookmakers_support"), DEFAULT_MIN_BOOKMAKERS_SUPPORT, minimum=0.0, maximum=20.0),
        "recommendations_only": _safe_bool(payload.get("recommendations_only"), False),
        "include_watch": _safe_bool(payload.get("include_watch"), True),
        "sort_by": "time" if str(payload.get("sort_by", "passability")).lower() == "time" else "passability",
        "limit": _coerce_int(payload.get("limit"), 120, minimum=1, maximum=500),
        "offset": _coerce_int(payload.get("offset"), 0, minimum=0, maximum=5000),
    }

    entry = _storefront_cache_entry(params, refresh=_safe_bool(payload.get("refresh"), False))
    events = entry["payload"].get("events", [])
    if not events:
        return {
            "match_info": {"league": "—", "home": "—", "away": "—", "status": "—"},
            "recommendations": [],
            "meta": {
                "total_events": 0,
                "window_hours": params["window_hours"],
                "sports_line": [],
            },
        }

    idx = _coerce_int(payload.get("event_index"), 0, minimum=0)
    event = events[idx % len(events)]
    return _state_payload_from_event(
        event,
        {
            "event_index": idx,
            "total_events": len(events),
            "window_hours": params["window_hours"],
            "sports_line": entry["payload"].get("sports_line", []),
            "source": "api/state",
        },
    )


@app.post("/get-ai-sports.php")
async def get_ai_sports(request: Request):
    payload = await _read_payload(request)
    get_all = _safe_bool(payload.get("get_all"), False)
    if get_all:
        _increment_fallback_usage("legacy_get_all")
        params = {
            "window_hours": _coerce_int(payload.get("window_hours"), DEFAULT_WINDOW_HOURS, minimum=1, maximum=72),
            "include_live": _safe_bool(payload.get("include_live"), True),
            "include_upcoming": _safe_bool(payload.get("include_upcoming"), True),
            "min_probability": _coerce_float(payload.get("min_probability"), 0.0, minimum=0.0, maximum=1.0),
            "min_coefficient": _coerce_float(payload.get("min_coefficient"), 1.0, minimum=1.0, maximum=50.0),
            "min_support": _coerce_float(payload.get("min_bookmakers_support"), 0.0, minimum=0.0, maximum=20.0),
            "recommendations_only": _safe_bool(payload.get("recommendations_only"), False),
            "include_watch": _safe_bool(payload.get("include_watch"), True),
            "sort_by": "time" if str(payload.get("sort_by", "passability")).lower() == "time" else "passability",
            "limit": _coerce_int(payload.get("limit"), 120, minimum=1, maximum=500),
            "offset": _coerce_int(payload.get("offset"), 0, minimum=0, maximum=5000),
        }
        entry = _storefront_cache_entry(params, refresh=_safe_bool(payload.get("refresh"), False))
        return entry["payload"]

    if payload.get("event_index") is not None:
        _increment_fallback_usage("event_index_mode")
    return await get_state(request)


@app.get("/api/events/{sport}")
async def get_events_by_sport(
    sport: str,
    window_hours: int = DEFAULT_WINDOW_HOURS,
    include_live: bool = True,
    include_upcoming: bool = True,
    recommendations_only: bool = False,
):
    params = {
        "window_hours": _coerce_int(window_hours, DEFAULT_WINDOW_HOURS, minimum=1, maximum=72),
        "include_live": _safe_bool(include_live, True),
        "include_upcoming": _safe_bool(include_upcoming, True),
        "min_probability": DEFAULT_MIN_PROBABILITY,
        "min_coefficient": DEFAULT_MIN_COEFFICIENT,
        "min_support": DEFAULT_MIN_BOOKMAKERS_SUPPORT,
        "recommendations_only": _safe_bool(recommendations_only, False),
        "include_watch": True,
        "sort_by": "passability",
        "limit": 500,
        "offset": 0,
    }
    entry = _storefront_cache_entry(params, refresh=False)
    events = [e for e in entry["payload"].get("events", []) if str(e.get("sport", "")).lower() == sport.lower()]
    return {"sport": sport, "total": len(events), "events": events}


@app.get("/api/sports")
async def get_sports_list(
    window_hours: int = DEFAULT_WINDOW_HOURS,
    include_live: bool = True,
    include_upcoming: bool = True,
):
    params = {
        "window_hours": _coerce_int(window_hours, DEFAULT_WINDOW_HOURS, minimum=1, maximum=72),
        "include_live": _safe_bool(include_live, True),
        "include_upcoming": _safe_bool(include_upcoming, True),
        "min_probability": DEFAULT_MIN_PROBABILITY,
        "min_coefficient": DEFAULT_MIN_COEFFICIENT,
        "min_support": DEFAULT_MIN_BOOKMAKERS_SUPPORT,
        "recommendations_only": False,
        "include_watch": True,
        "sort_by": "passability",
        "limit": 500,
        "offset": 0,
    }
    entry = _storefront_cache_entry(params, refresh=False)
    sports = entry["payload"].get("sports", {})
    return {
        "sports": sports,
        "sports_line": entry["payload"].get("sports_line", []),
        "total_events": entry["payload"].get("total", 0),
    }


@app.get("/api/analytics/events")
async def analytics_events(
    window_hours: int = DEFAULT_WINDOW_HOURS,
    include_live: bool = True,
    include_upcoming: bool = True,
    include_scored: bool = True,
):
    raw_events = _collect_raw_events(
        _coerce_int(window_hours, DEFAULT_WINDOW_HOURS, minimum=1, maximum=72),
        _safe_bool(include_live, True),
        _safe_bool(include_upcoming, True),
    )
    payload: Dict[str, Any] = {
        "total_raw_events": len(raw_events),
        "raw_events": raw_events,
        "generated_at": _now_utc().isoformat(),
    }

    if _safe_bool(include_scored, True):
        scored = [
            _prepare_event(event, 0.0, 1.0, 0.0)
            for event in raw_events
        ]
        _sort_events(scored, "passability")
        payload["scored_events"] = scored
        payload["sports"] = _build_sports_map(scored)
    return payload


@app.get("/api/metrics")
async def api_metrics():
    alerts = _build_alerts()
    with _metrics_lock:
        requests_total = _metrics["requests_total"]
        errors_total = _metrics["errors_total"]
        cache_hits = _metrics["cache_hits"]
        cache_misses = _metrics["cache_misses"]
        cache_total = cache_hits + cache_misses
        cache_hit_ratio = (cache_hits / cache_total) if cache_total else 0.0
        error_rate = (errors_total / requests_total) if requests_total else 0.0
        metrics_snapshot = copy.deepcopy(_metrics)
        runtime_snapshot = copy.deepcopy(_runtime_state)

    return {
        "summary": {
            "requests_total": requests_total,
            "errors_total": errors_total,
            "error_rate": round(error_rate, 6),
            "cache_hits": cache_hits,
            "cache_misses": cache_misses,
            "cache_hit_ratio": round(cache_hit_ratio, 6),
        },
        "runtime": runtime_snapshot,
        "alerts": alerts,
        "metrics": metrics_snapshot,
        "timestamp": _now_utc().isoformat(),
    }


@app.get("/api/source-status")
async def source_status():
    alerts = _build_alerts()
    with _metrics_lock:
        cache_size = len(_cache)
        low_streak = _runtime_state["low_event_streak"]
    return {
        "status": "ok",
        "version": "14.0",
        "cache": {
            "ttl_seconds": CACHE_TTL_SECONDS,
            "entries": cache_size,
        },
        "quality": {
            "default_min_probability": DEFAULT_MIN_PROBABILITY,
            "default_min_coefficient": DEFAULT_MIN_COEFFICIENT,
            "default_min_bookmakers_support": DEFAULT_MIN_BOOKMAKERS_SUPPORT,
            "max_odds_age_seconds": MAX_ODDS_AGE_SECONDS,
            "stale_odds_penalty_factor": STALE_ODDS_PENALTY_FACTOR,
        },
        "runtime": {
            "low_event_streak": low_streak,
            "last_storefront_total": _runtime_state["last_storefront_total"],
            "last_storefront_generated_at": _runtime_state["last_storefront_generated_at"],
        },
        "alerts": alerts,
        "timestamp": _now_utc().isoformat(),
    }


@app.get("/api/debug")
async def debug_info():
    sample = _collect_raw_events(window_hours=24, include_live=True, include_upcoming=True)[:5]
    return {
        "version": "14.0",
        "sample_events": sample,
        "timestamp": _now_utc().isoformat(),
    }


if __name__ == "__main__":
    import uvicorn

    target_port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=target_port)
