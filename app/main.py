# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.0 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

import copy
import datetime
import hashlib
import html
import json
import logging
import os
import pathlib
import random
import re
import sys
import threading
import time
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError

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


def _load_env_pack_defaults() -> Dict[str, str]:
    """Load defaults from docs/external_donor_pack.env if present."""
    pack_path = pathlib.Path(__file__).resolve().parents[1] / "docs" / "external_donor_pack.env"
    if not pack_path.exists():
        return {}

    defaults: Dict[str, str] = {}
    try:
        for raw_line in pack_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            defaults[key.strip()] = value.strip()
    except Exception:
        return {}
    return defaults


def _env_default(name: str, fallback: str) -> str:
    return _ENV_PACK_DEFAULTS.get(name, fallback)


def _normalize_json_env_value(value: str) -> str:
    raw = str(value or "").strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in {'"', "'"}:
        return raw[1:-1]
    return raw


_ENV_PACK_DEFAULTS = _load_env_pack_defaults()


# ============================================
# КОНФИГ
# ============================================

CACHE_TTL_SECONDS = int(os.getenv("STORE_CACHE_TTL_SECONDS", "30"))
DONOR_CACHE_TTL_SECONDS = int(os.getenv("DONOR_CACHE_TTL_SECONDS", "45"))
LOW_EVENT_ALERT_THRESHOLD = int(os.getenv("LOW_EVENT_ALERT_THRESHOLD", "4"))
LOW_EVENT_STREAK_ALERT = int(os.getenv("LOW_EVENT_STREAK_ALERT", "3"))
LOW_DONOR_COVERAGE_THRESHOLD = float(os.getenv("LOW_DONOR_COVERAGE_THRESHOLD", "0.35"))
LOW_DONOR_COVERAGE_STREAK_ALERT = int(os.getenv("LOW_DONOR_COVERAGE_STREAK_ALERT", "3"))

DEFAULT_WINDOW_HOURS = int(os.getenv("DEFAULT_WINDOW_HOURS", "24"))
DEFAULT_MIN_PROBABILITY = float(os.getenv("DEFAULT_MIN_PROBABILITY", "0.6"))
DEFAULT_MIN_COEFFICIENT = float(os.getenv("DEFAULT_MIN_COEFFICIENT", "1.5"))
DEFAULT_MIN_BOOKMAKERS_SUPPORT = float(os.getenv("DEFAULT_MIN_BOOKMAKERS_SUPPORT", "2.0"))
EXTERNAL_CONSENSUS_MIN_SOURCES = int(os.getenv("EXTERNAL_CONSENSUS_MIN_SOURCES", _env_default("EXTERNAL_CONSENSUS_MIN_SOURCES", "3")))
EXTERNAL_CONSENSUS_ENABLED = os.getenv("EXTERNAL_CONSENSUS_ENABLED", _env_default("EXTERNAL_CONSENSUS_ENABLED", "false")).strip().lower() in {"1", "true", "yes", "on"}
EXTERNAL_DONOR_INGESTION_ENABLED = os.getenv(
    "EXTERNAL_DONOR_INGESTION_ENABLED",
    _env_default("EXTERNAL_DONOR_INGESTION_ENABLED", "false"),
).strip().lower() in {"1", "true", "yes", "on"}
EXTERNAL_DONOR_RANDOM_SEED = os.getenv("EXTERNAL_DONOR_RANDOM_SEED", "prizolov-donor-seed")
EXTERNAL_DONOR_CATALOG_EXTRA_JSON = _normalize_json_env_value(os.getenv("EXTERNAL_DONOR_CATALOG_EXTRA_JSON", _env_default("EXTERNAL_DONOR_CATALOG_EXTRA_JSON", "")))
EXTERNAL_DONOR_JSON_FEEDS = _normalize_json_env_value(os.getenv("EXTERNAL_DONOR_JSON_FEEDS", _env_default("EXTERNAL_DONOR_JSON_FEEDS", "")))
EXTERNAL_DONOR_RSS_FEEDS = _normalize_json_env_value(os.getenv("EXTERNAL_DONOR_RSS_FEEDS", _env_default("EXTERNAL_DONOR_RSS_FEEDS", "")))
EXTERNAL_DONOR_TEXT_FEEDS = _normalize_json_env_value(os.getenv("EXTERNAL_DONOR_TEXT_FEEDS", _env_default("EXTERNAL_DONOR_TEXT_FEEDS", "")))
EXTERNAL_DONOR_HTTP_TIMEOUT_SECONDS = int(os.getenv("EXTERNAL_DONOR_HTTP_TIMEOUT_SECONDS", _env_default("EXTERNAL_DONOR_HTTP_TIMEOUT_SECONDS", "5")))
EXTERNAL_DONOR_HTTP_MAX_BODY_BYTES = int(os.getenv("EXTERNAL_DONOR_HTTP_MAX_BODY_BYTES", _env_default("EXTERNAL_DONOR_HTTP_MAX_BODY_BYTES", "850000")))
EXTERNAL_DONOR_RSS_ITEM_LIMIT = int(os.getenv("EXTERNAL_DONOR_RSS_ITEM_LIMIT", _env_default("EXTERNAL_DONOR_RSS_ITEM_LIMIT", "50")))
EXTERNAL_DONOR_TEXT_ITEM_LIMIT = int(os.getenv("EXTERNAL_DONOR_TEXT_ITEM_LIMIT", _env_default("EXTERNAL_DONOR_TEXT_ITEM_LIMIT", "60")))
EXTERNAL_DONOR_ENABLE_SYNTHETIC = os.getenv("EXTERNAL_DONOR_ENABLE_SYNTHETIC", _env_default("EXTERNAL_DONOR_ENABLE_SYNTHETIC", "false")).strip().lower() in {"1", "true", "yes", "on"}
EXTERNAL_DONOR_SIGNAL_LIMIT_PER_EVENT = int(os.getenv("EXTERNAL_DONOR_SIGNAL_LIMIT_PER_EVENT", _env_default("EXTERNAL_DONOR_SIGNAL_LIMIT_PER_EVENT", "10")))



def _external_donors_active() -> bool:
    """External donor pipeline is opt-in only (off by default)."""
    return EXTERNAL_DONOR_INGESTION_ENABLED and EXTERNAL_CONSENSUS_ENABLED


MAX_ODDS_AGE_SECONDS = int(os.getenv("MAX_ODDS_AGE_SECONDS", "900"))  # 15 минут
STALE_ODDS_PENALTY_FACTOR = float(os.getenv("STALE_ODDS_PENALTY_FACTOR", "0.92"))
MAX_LIVE_EVENT_AGE_HOURS = float(os.getenv("MAX_LIVE_EVENT_AGE_HOURS", "4"))


# ============================================
# ДАННЫЕ (LIVE + UPCOMING)
# ============================================

# Demo templates moved to demo_storefront_events.py (off by default).
STOREFRONT_DEMO_EVENTS_ENABLED = os.getenv(
    "STOREFRONT_DEMO_EVENTS_ENABLED",
    _env_default("STOREFRONT_DEMO_EVENTS_ENABLED", "false"),
).strip().lower() in {"1", "true", "yes", "on"}


def _live_events_catalog() -> List[Dict[str, Any]]:
    if not STOREFRONT_DEMO_EVENTS_ENABLED:
        return []
    from demo_storefront_events import LIVE_EVENTS  # noqa: WPS433

    return LIVE_EVENTS


def _upcoming_event_templates() -> List[tuple]:
    if not STOREFRONT_DEMO_EVENTS_ENABLED:
        return []
    from demo_storefront_events import UPCOMING_EVENT_TEMPLATES  # noqa: WPS433

    return UPCOMING_EVENT_TEMPLATES





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
    "donor_pipeline": {
        "catalog_total": 0,
        "active_total": 0,
        "signals_total": 0,
        "events_with_consensus": 0,
        "consensus_coverage": 0.0,
        "last_generated_at": None,
    },
    "endpoints": {},
}

_runtime_state: Dict[str, Any] = {
    "low_event_streak": 0,
    "last_storefront_total": 0,
    "last_storefront_generated_at": None,
    "low_donor_coverage_streak": 0,
    "last_donor_coverage_ratio": 0.0,
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
        low_donor_streak = _runtime_state.get("low_donor_coverage_streak", 0)
        donor_coverage = _runtime_state.get("last_donor_coverage_ratio", 0.0)
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

        if low_donor_streak >= LOW_DONOR_COVERAGE_STREAK_ALERT:
            alerts.append(
                {
                    "level": "warning",
                    "code": "low_donor_coverage_streak",
                    "message": f"Низкое покрытие внешнего консенсуса: {round(donor_coverage * 100, 2)}% ({low_donor_streak} циклов).",
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



def _slugify_text(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9а-я]+", "-", str(value).lower(), flags=re.IGNORECASE)
    cleaned = re.sub(r"-+", "-", cleaned).strip("-")
    return cleaned or "unknown"


def _normalize_team_name(value: str) -> str:
    text_value = str(value or "").lower()
    text_value = re.sub(r"[^a-z0-9а-я ]+", "", text_value, flags=re.IGNORECASE)
    text_value = re.sub(r"\s+", " ", text_value).strip()
    return text_value


def _event_match_key(event: Dict[str, Any]) -> str:
    return "|".join([
        _normalize_team_name(event.get("home", "")),
        _normalize_team_name(event.get("away", "")),
        str(event.get("sport", "unknown")).lower(),
    ])


def _default_donor_catalog() -> List[Dict[str, Any]]:
    """Built-in donor catalog disabled — use only vetted EXTERNAL_DONOR_* env feeds."""
    return []


def _load_extra_donor_catalog() -> List[Dict[str, Any]]:
    if not EXTERNAL_DONOR_CATALOG_EXTRA_JSON.strip():
        return []
    try:
        payload = json.loads(EXTERNAL_DONOR_CATALOG_EXTRA_JSON)
    except Exception:
        logger.warning("⚠️ Failed to parse EXTERNAL_DONOR_CATALOG_EXTRA_JSON")
        return []

    if not isinstance(payload, list):
        return []

    extras: List[Dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        donor_id = _slugify_text(str(item.get("id") or item.get("name") or "extra-donor"))
        extras.append(
            {
                "id": donor_id,
                "name": str(item.get("name") or donor_id),
                "channel": str(item.get("channel") or "external"),
                "weight": _coerce_float(item.get("weight"), 1.0, minimum=0.2, maximum=3.0),
                "active": _safe_bool(item.get("active"), True),
                "url": item.get("url"),
            }
        )
    return extras


def _resolve_donor_catalog() -> List[Dict[str, Any]]:
    catalog = _default_donor_catalog()
    extras = _load_extra_donor_catalog()
    merged: Dict[str, Dict[str, Any]] = {item["id"]: item for item in catalog}
    for item in extras:
        merged[item["id"]] = item
    return list(merged.values())


def _donor_noise(seed: str, min_value: float, max_value: float) -> float:
    digest = hashlib.sha256((EXTERNAL_DONOR_RANDOM_SEED + seed).encode("utf-8")).hexdigest()
    span = max_value - min_value
    ratio = int(digest[:8], 16) / float(0xFFFFFFFF)
    return min_value + span * ratio


def _parse_feed_sources_env(raw_env: str, fallback_prefix: str, channel: str) -> List[Dict[str, Any]]:
    normalized_env = _normalize_json_env_value(raw_env)
    if not normalized_env.strip():
        return []

    try:
        payload = json.loads(normalized_env)
    except Exception:
        logger.warning(f"⚠️ Failed to parse {fallback_prefix} feed configuration")
        return []

    if isinstance(payload, str):
        payload = [{"url": payload}]
    if not isinstance(payload, list):
        return []

    feeds: List[Dict[str, Any]] = []
    for idx, item in enumerate(payload):
        if isinstance(item, str):
            item = {"url": item}
        if not isinstance(item, dict):
            continue

        url = str(item.get("url") or "").strip()
        if not url:
            continue

        donor_id = _slugify_text(str(item.get("donor_id") or f"{fallback_prefix}-{idx+1}"))
        feeds.append(
            {
                "url": url,
                "donor_id": donor_id,
                "donor_name": str(item.get("donor_name") or donor_id),
                "channel": str(item.get("channel") or channel),
                "weight": _coerce_float(item.get("weight"), 1.0, minimum=0.2, maximum=3.0),
                "sport": str(item.get("sport") or "").strip().lower() or None,
            }
        )
    return feeds


def _parse_external_feed_sources() -> List[Dict[str, Any]]:
    if not _external_donors_active():
        return []
    return _parse_feed_sources_env(EXTERNAL_DONOR_JSON_FEEDS, "json-feed", "json-feed")


def _parse_external_rss_sources() -> List[Dict[str, Any]]:
    if not _external_donors_active():
        return []
    return _parse_feed_sources_env(EXTERNAL_DONOR_RSS_FEEDS, "rss-feed", "rss")


def _parse_external_text_sources() -> List[Dict[str, Any]]:
    if not _external_donors_active():
        return []
    return _parse_feed_sources_env(EXTERNAL_DONOR_TEXT_FEEDS, "text-feed", "text-feed")


def _fetch_external_feed_content(url: str) -> Optional[str]:
    try:
        req = urllib_request.Request(
            url,
            headers={
                "User-Agent": "PrizolovDonorCollector/1.0",
                "Accept": "application/json, application/rss+xml, application/xml, text/plain, */*",
            },
        )
        with urllib_request.urlopen(req, timeout=EXTERNAL_DONOR_HTTP_TIMEOUT_SECONDS) as response:
            payload = response.read(EXTERNAL_DONOR_HTTP_MAX_BODY_BYTES + 1)
            if len(payload) > EXTERNAL_DONOR_HTTP_MAX_BODY_BYTES:
                payload = payload[:EXTERNAL_DONOR_HTTP_MAX_BODY_BYTES]
            charset = None
            try:
                charset = response.headers.get_content_charset()
            except Exception:
                charset = None
        return payload.decode(charset or "utf-8", errors="ignore")
    except (URLError, HTTPError, TimeoutError, ValueError):
        return None
    except Exception:
        return None


def _build_event_lookup(events_by_key: Dict[str, Dict[str, Any]]) -> List[Tuple[str, Dict[str, Any], str, str, str]]:
    lookup: List[Tuple[str, Dict[str, Any], str, str, str]] = []
    for key, event in events_by_key.items():
        home_norm = _normalize_team_name(event.get("home", ""))
        away_norm = _normalize_team_name(event.get("away", ""))
        sport_norm = str(event.get("sport", "")).strip().lower()
        if home_norm and away_norm:
            lookup.append((key, event, home_norm, away_norm, sport_norm))
    return lookup


def _best_event_match_for_text(
    text: str,
    event_lookup: List[Tuple[str, Dict[str, Any], str, str, str]],
    sport_hint: Optional[str] = None,
) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    norm_text = _normalize_team_name(text)
    if not norm_text:
        return None, None

    best_key: Optional[str] = None
    best_event: Optional[Dict[str, Any]] = None
    best_score = -1.0
    sport_hint_norm = str(sport_hint or "").strip().lower()

    for key, event, home_norm, away_norm, sport_norm in event_lookup:
        score = 0.0
        if home_norm in norm_text:
            score += 1.0
        if away_norm in norm_text:
            score += 1.0
        if score < 2.0:
            continue
        if sport_hint_norm and sport_norm and sport_norm == sport_hint_norm:
            score += 0.25
        if score > best_score:
            best_score = score
            best_key = key
            best_event = event

    return best_key, best_event


def _extract_probability_from_text(text: str) -> Optional[float]:
    patterns = [
        r"(?:probability|prob|вероятн(?:ость|ости)?|проходим(?:ость|остью)?)\s*[:=]?\s*(\d{1,3}(?:[\.,]\d+)?)\s*%?",
        r"(\d{1,3}(?:[\.,]\d+)?)\s*%",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        raw = match.group(1).replace(",", ".")
        try:
            value = float(raw)
        except ValueError:
            continue
        if value > 1.0:
            value /= 100.0
        return _coerce_float(value, 0.0, minimum=0.01, maximum=0.99)
    return None


def _extract_coefficient_from_text(text: str) -> Optional[float]:
    patterns = [
        r"(?:odds?|коэф(?:фициент)?)\s*[:=]?\s*(\d{1,2}(?:[\.,]\d{1,2})?)",
        r"(?:k|к)\s*[:=]\s*(\d{1,2}(?:[\.,]\d{1,2})?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        raw = match.group(1).replace(",", ".")
        try:
            value = float(raw)
        except ValueError:
            continue
        return _coerce_float(value, 1.5, minimum=1.01, maximum=50.0)
    return None


def _extract_line_from_text(text: str) -> Optional[str]:
    probes = [
        "тотал больше",
        "тотал меньше",
        "обе забьют",
        "победа 1",
        "победа 2",
        "фора",
        "double chance",
        "moneyline",
        "draw no bet",
    ]
    text_norm = text.lower()
    for probe in probes:
        idx = text_norm.find(probe)
        if idx == -1:
            continue
        snippet = text[idx: idx + 96].strip()
        snippet = re.split(r"[\n\r\|]", snippet)[0].strip()
        if snippet:
            return snippet[:96]

    pieces = [part.strip() for part in re.split(r"[\n\r]+", text) if part.strip()]
    if pieces:
        return pieces[0][:96]
    return None


def _event_fallback_pick(event: Dict[str, Any], donor_seed: str) -> Tuple[str, float, float]:
    rec_pool = event.get("all_recommendations") or event.get("recommendations") or []
    if rec_pool:
        idx = int(_donor_noise(donor_seed + ":pick", 0, max(0, len(rec_pool) - 1)))
        rec = rec_pool[idx]
        line = str(rec.get("line") or "Исход")
        prob = _coerce_float(rec.get("adjusted_probability", rec.get("probability", 0.62)), 0.62, minimum=0.02, maximum=0.99)
        coef = _coerce_float(rec.get("coefficient"), 1.7, minimum=1.01, maximum=50.0)
        return line, prob, coef
    return "Исход", 0.62, 1.7


def _build_external_signal(
    *,
    event: Dict[str, Any],
    event_key: str,
    line: str,
    probability: float,
    coefficient: float,
    source_id: str,
    source_name: str,
    source_channel: str,
    source_weight: float,
    source_url: Optional[str],
    captured_at: str,
) -> Dict[str, Any]:
    return {
        "event_id": event.get("id"),
        "event_key": event_key,
        "line": line,
        "probability": round(_coerce_float(probability, 0.0, minimum=0.0, maximum=1.0), 4),
        "coefficient": round(_coerce_float(coefficient, 1.01, minimum=1.01, maximum=50.0), 2),
        "source_id": source_id,
        "source_name": source_name,
        "source_channel": source_channel,
        "source_weight": _coerce_float(source_weight, 1.0, minimum=0.1, maximum=5.0),
        "captured_at": captured_at,
        "source_url": source_url,
    }


def _load_json_feed_signals(events_by_key: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    feeds = _parse_external_feed_sources()
    if not feeds:
        return []

    event_lookup = _build_event_lookup(events_by_key)
    signals: List[Dict[str, Any]] = []
    now_iso = _now_utc().isoformat()

    for feed in feeds:
        raw = _fetch_external_feed_content(feed["url"])
        if not raw:
            continue

        try:
            payload = json.loads(raw)
        except Exception:
            continue

        if isinstance(payload, dict):
            records = payload.get("predictions") or payload.get("items") or payload.get("data") or payload.get("messages") or []
        else:
            records = payload
        if not isinstance(records, list):
            continue

        for rec in records[:EXTERNAL_DONOR_TEXT_ITEM_LIMIT]:
            if not isinstance(rec, dict):
                continue

            event_key = "|".join(
                [
                    _normalize_team_name(rec.get("home", "")),
                    _normalize_team_name(rec.get("away", "")),
                    str(rec.get("sport", feed.get("sport") or "unknown")).lower(),
                ]
            )
            event = events_by_key.get(event_key)

            if event is None:
                rec_text = " ".join(
                    [
                        str(rec.get("title") or ""),
                        str(rec.get("text") or ""),
                        str(rec.get("description") or ""),
                    ]
                )
                event_key, event = _best_event_match_for_text(rec_text, event_lookup, sport_hint=rec.get("sport") or feed.get("sport"))
            if event is None or event_key is None:
                    continue

            line_fb, prob_fb, coef_fb = _event_fallback_pick(event, f"{feed['donor_id']}:{event.get('id')}")
            line = str(rec.get("line") or rec.get("market") or rec.get("tip") or _extract_line_from_text(str(rec.get("text") or "")) or line_fb)
            probability = _coerce_float(
                rec.get("probability", rec.get("prob", rec.get("passability", _extract_probability_from_text(str(rec.get("text") or "")) or prob_fb))),
                prob_fb,
                minimum=0.02,
                maximum=0.99,
            )
            coefficient = _coerce_float(
                rec.get("coefficient", rec.get("odds", _extract_coefficient_from_text(str(rec.get("text") or "")) or coef_fb)),
                coef_fb,
                minimum=1.01,
                maximum=50.0,
            )

            signals.append(
                _build_external_signal(
                    event=event,
                    event_key=event_key,
                    line=line,
                    probability=probability,
                    coefficient=coefficient,
                    source_id=str(rec.get("source_id") or feed["donor_id"]),
                    source_name=str(rec.get("source_name") or feed["donor_name"]),
                    source_channel=str(rec.get("source_channel") or feed["channel"]),
                    source_weight=_coerce_float(rec.get("source_weight"), feed["weight"], minimum=0.2, maximum=3.0),
                    source_url=str(rec.get("source_url") or feed["url"]),
                    captured_at=now_iso,
                )
            )

    return signals


def _load_rss_feed_signals(events_by_key: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    feeds = _parse_external_rss_sources()
    if not feeds:
        return []

    event_lookup = _build_event_lookup(events_by_key)
    signals: List[Dict[str, Any]] = []
    now_iso = _now_utc().isoformat()

    atom_ns = "{http://www.w3.org/2005/Atom}"
    for feed in feeds:
        raw = _fetch_external_feed_content(feed["url"])
        if not raw:
            continue

        try:
            root = ET.fromstring(raw)
        except ET.ParseError:
            continue

        items = list(root.findall(".//item"))
        if not items:
            items = list(root.findall(f".//{atom_ns}entry"))

        for item in items[:EXTERNAL_DONOR_RSS_ITEM_LIMIT]:
            title = item.findtext("title") or item.findtext(f"{atom_ns}title") or ""
            description = (
                item.findtext("description")
                or item.findtext("summary")
                or item.findtext(f"{atom_ns}summary")
                or item.findtext(f"{atom_ns}content")
                or ""
            )
            link = item.findtext("link") or item.findtext(f"{atom_ns}link") or feed["url"]

            text_blob = html.unescape(f"{title} {description}")
            event_key, event = _best_event_match_for_text(text_blob, event_lookup, sport_hint=feed.get("sport"))
            if event is None or event_key is None:
                continue

            line_fb, prob_fb, coef_fb = _event_fallback_pick(event, f"rss:{feed['donor_id']}:{event.get('id')}")
            line = _extract_line_from_text(text_blob) or line_fb
            probability = _extract_probability_from_text(text_blob) or prob_fb
            coefficient = _extract_coefficient_from_text(text_blob) or coef_fb

            signals.append(
                _build_external_signal(
                    event=event,
                    event_key=event_key,
                    line=line,
                    probability=probability,
                    coefficient=coefficient,
                    source_id=feed["donor_id"],
                    source_name=feed["donor_name"],
                    source_channel=feed["channel"],
                    source_weight=feed["weight"],
                    source_url=link,
                    captured_at=now_iso,
                )
            )

    return signals


def _load_text_feed_signals(events_by_key: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    feeds = _parse_external_text_sources()
    if not feeds:
        return []

    event_lookup = _build_event_lookup(events_by_key)
    signals: List[Dict[str, Any]] = []
    now_iso = _now_utc().isoformat()

    for feed in feeds:
        raw = _fetch_external_feed_content(feed["url"])
        if not raw:
            continue

        blocks: List[str] = []
        try:
            payload = json.loads(raw)
            if isinstance(payload, dict):
                payload = payload.get("messages") or payload.get("items") or payload.get("data") or []
            if isinstance(payload, list):
                for item in payload[:EXTERNAL_DONOR_TEXT_ITEM_LIMIT]:
                    if isinstance(item, dict):
                        blocks.append(
                            " ".join(
                                [
                                    str(item.get("title") or ""),
                                    str(item.get("text") or ""),
                                    str(item.get("description") or ""),
                                ]
                            )
                        )
                    elif isinstance(item, str):
                        blocks.append(item)
        except Exception:
            parts = [part.strip() for part in re.split(r"\n\s*\n", raw) if part.strip()]
            blocks.extend(parts[:EXTERNAL_DONOR_TEXT_ITEM_LIMIT])

        for block in blocks[:EXTERNAL_DONOR_TEXT_ITEM_LIMIT]:
            text_blob = html.unescape(str(block))
            event_key, event = _best_event_match_for_text(text_blob, event_lookup, sport_hint=feed.get("sport"))
            if event is None or event_key is None:
                continue

            line_fb, prob_fb, coef_fb = _event_fallback_pick(event, f"text:{feed['donor_id']}:{event.get('id')}")
            line = _extract_line_from_text(text_blob) or line_fb
            probability = _extract_probability_from_text(text_blob) or prob_fb
            coefficient = _extract_coefficient_from_text(text_blob) or coef_fb

            signals.append(
                _build_external_signal(
                    event=event,
                    event_key=event_key,
                    line=line,
                    probability=probability,
                    coefficient=coefficient,
                    source_id=feed["donor_id"],
                    source_name=feed["donor_name"],
                    source_channel=feed["channel"],
                    source_weight=feed["weight"],
                    source_url=feed["url"],
                    captured_at=now_iso,
                )
            )

    return signals


def _generate_synthetic_donor_signals(events: List[Dict[str, Any]], catalog: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    now_iso = _now_utc().isoformat()
    signals: List[Dict[str, Any]] = []

    for donor in catalog:
        if not donor.get("active", True):
            continue
        donor_id = str(donor.get("id"))
        donor_weight = _coerce_float(donor.get("weight"), 1.0, minimum=0.2, maximum=3.0)

        for event in events:
            event_id = str(event.get("id"))
            event_key = _event_match_key(event)
            coverage_rand = _donor_noise(donor_id + ":" + event_id + ":coverage", 0.0, 1.0)
            if coverage_rand > 0.56:
                continue

            pool = event.get("all_recommendations") or []
            if not pool:
                continue

            top_pick_idx = int(_donor_noise(donor_id + ":" + event_id + ":pick", 0, min(2, len(pool) - 1)))
            base = pool[top_pick_idx]

            probability_delta = _donor_noise(donor_id + ":" + event_id + ":pdelta", -0.06, 0.05)
            coefficient_delta = _donor_noise(donor_id + ":" + event_id + ":cdelta", -0.08, 0.08)

            probability = _coerce_float(base.get("adjusted_probability", base.get("probability", 0.0)) + probability_delta, 0.0, minimum=0.02, maximum=0.98)
            coefficient = _coerce_float(base.get("coefficient", 1.5) * (1.0 + coefficient_delta), 1.5, minimum=1.01, maximum=50.0)

            signals.append(
                {
                    "event_id": event_id,
                    "event_key": event_key,
                    "line": base.get("line", "Исход"),
                    "probability": round(probability, 4),
                    "coefficient": round(coefficient, 2),
                    "source_id": donor_id,
                    "source_name": donor.get("name", donor_id),
                    "source_channel": donor.get("channel", "external"),
                    "source_weight": donor_weight,
                    "captured_at": now_iso,
                    "source_url": donor.get("url"),
                }
            )

    return signals


def _build_external_consensus(
    events: List[Dict[str, Any]],
    donor_signals: List[Dict[str, Any]],
    min_sources: int,
) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for sig in donor_signals:
        event_id = str(sig.get("event_id") or "")
        if not event_id:
            continue
        grouped.setdefault(event_id, []).append(sig)

    consensus_map: Dict[str, Dict[str, Any]] = {}
    consensus_top: List[Dict[str, Any]] = []

    for event in events:
        event_id = str(event.get("id") or "")
        signals = grouped.get(event_id, [])
        if not signals:
            continue

        unique_sources = sorted({str(s.get("source_id")) for s in signals if s.get("source_id")})
        donors_total = len(unique_sources)

        line_groups: Dict[str, Dict[str, Any]] = {}
        for sig in signals:
            line = str(sig.get("line") or "Исход")
            entry = line_groups.setdefault(line, {"weighted_prob": 0.0, "weighted_coef": 0.0, "weight_total": 0.0, "count": 0})
            weight = _coerce_float(sig.get("source_weight"), 1.0, minimum=0.1, maximum=5.0)
            entry["weighted_prob"] += _coerce_float(sig.get("probability"), 0.0, minimum=0.0, maximum=1.0) * weight
            entry["weighted_coef"] += _coerce_float(sig.get("coefficient"), 1.0, minimum=1.01, maximum=50.0) * weight
            entry["weight_total"] += weight
            entry["count"] += 1

        ranked_lines: List[Tuple[str, Dict[str, Any]]] = []
        for line, grp in line_groups.items():
            if grp["weight_total"] <= 0:
                continue
            avg_prob = grp["weighted_prob"] / grp["weight_total"]
            avg_coef = grp["weighted_coef"] / grp["weight_total"]
            score = avg_prob * 0.75 + min(grp["count"] / max(donors_total, 1), 1.0) * 0.25
            ranked_lines.append((line, {"avg_prob": avg_prob, "avg_coef": avg_coef, "score": score, **grp}))

        if not ranked_lines:
            continue

        ranked_lines.sort(key=lambda item: (-item[1]["score"], -item[1]["avg_prob"], item[0]))
        best_line, best_metrics = ranked_lines[0]

        total_weight = sum(item[1]["weight_total"] for item in ranked_lines) or 1.0
        agreement_score = best_metrics["weight_total"] / total_weight

        ready = donors_total >= max(1, min_sources)
        confidence_tier = "low"
        if ready and best_metrics["avg_prob"] >= 0.72 and agreement_score >= 0.45:
            confidence_tier = "high"
        elif ready and best_metrics["avg_prob"] >= 0.64 and agreement_score >= 0.32:
            confidence_tier = "medium"

        sample_sources = sorted(signals, key=lambda s: (-_coerce_float(s.get("source_weight"), 1.0), -_coerce_float(s.get("probability"), 0.0)))
        sample_sources = sample_sources[:12]

        consensus = {
            "ready": ready,
            "line": best_line,
            "consensus_probability": round(best_metrics["avg_prob"], 4),
            "consensus_coefficient": round(best_metrics["avg_coef"], 2),
            "donors_total": donors_total,
            "signals_total": len(signals),
            "agreement_score": round(agreement_score, 4),
            "support_weight": round(best_metrics["weight_total"], 4),
            "confidence_tier": confidence_tier,
            "updated_at": _now_utc().isoformat(),
            "sources": [
                {
                    "source_id": s.get("source_id"),
                    "source_name": s.get("source_name"),
                    "source_channel": s.get("source_channel"),
                    "source_weight": s.get("source_weight"),
                    "probability": s.get("probability"),
                    "coefficient": s.get("coefficient"),
                    "line": s.get("line"),
                }
                for s in sample_sources
            ],
        }

        consensus_map[event_id] = consensus

        consensus_top.append(
            {
                "event_id": event_id,
                "sport": event.get("sport"),
                "league": event.get("league"),
                "home": event.get("home"),
                "away": event.get("away"),
                "is_live": event.get("is_live", False),
                "time": event.get("time"),
                **consensus,
            }
        )

    consensus_top.sort(
        key=lambda item: (
            -_coerce_float(item.get("consensus_probability"), 0.0),
            -_coerce_float(item.get("agreement_score"), 0.0),
            -_coerce_int(item.get("donors_total"), 0),
        )
    )

    events_with_consensus = len(consensus_map)
    coverage_ratio = (events_with_consensus / len(events)) if events else 0.0

    donor_summary = {
        "signals_total": len(donor_signals),
        "events_with_consensus": events_with_consensus,
        "consensus_coverage": round(coverage_ratio, 4),
        "min_sources_required": max(1, min_sources),
    }
    return consensus_map, consensus_top, donor_summary


def _apply_external_consensus(events: List[Dict[str, Any]], min_sources: int) -> Tuple[List[Dict[str, Any]], Dict[str, Any], List[Dict[str, Any]]]:
    if not _external_donors_active():
        for event in events:
            event["external_consensus"] = None
        with _metrics_lock:
            _metrics["donor_pipeline"].update(
                {
                    "catalog_total": 0,
                    "active_total": 0,
                    "signals_total": 0,
                    "events_with_consensus": 0,
                    "consensus_coverage": 0.0,
                    "last_generated_at": _now_utc().isoformat(),
                }
            )
            _runtime_state["last_donor_coverage_ratio"] = 0.0
            _runtime_state["low_donor_coverage_streak"] = 0
        return events, {
            "enabled": False,
            "ingestion_enabled": EXTERNAL_DONOR_INGESTION_ENABLED,
            "consensus_enabled": EXTERNAL_CONSENSUS_ENABLED,
        }, []

    catalog = _resolve_donor_catalog()
    active_catalog = [d for d in catalog if d.get("active", True)]

    events_by_key = {_event_match_key(e): e for e in events}

    synthetic_signals: List[Dict[str, Any]] = []
    if EXTERNAL_DONOR_ENABLE_SYNTHETIC:
        synthetic_signals = _generate_synthetic_donor_signals(events, active_catalog)

    json_feed_signals = _load_json_feed_signals(events_by_key)
    rss_feed_signals = _load_rss_feed_signals(events_by_key)
    text_feed_signals = _load_text_feed_signals(events_by_key)
    all_signals = synthetic_signals + json_feed_signals + rss_feed_signals + text_feed_signals

    grouped_count: Dict[str, int] = {}
    trimmed_signals: List[Dict[str, Any]] = []
    for sig in all_signals:
        event_id = str(sig.get("event_id") or "")
        if not event_id:
            continue
        cnt = grouped_count.get(event_id, 0)
        if cnt >= EXTERNAL_DONOR_SIGNAL_LIMIT_PER_EVENT:
            continue
        grouped_count[event_id] = cnt + 1
        trimmed_signals.append(sig)

    consensus_map, consensus_top, donor_summary = _build_external_consensus(
        events,
        trimmed_signals,
        max(1, min_sources),
    )

    for event in events:
        event_id = str(event.get("id") or "")
        event["external_consensus"] = consensus_map.get(event_id)

    coverage = _coerce_float(donor_summary.get("consensus_coverage"), 0.0, minimum=0.0, maximum=1.0)
    with _metrics_lock:
        _metrics["donor_pipeline"].update(
            {
                "catalog_total": len(catalog),
                "active_total": len(active_catalog),
                "signals_total": len(trimmed_signals),
                "events_with_consensus": donor_summary.get("events_with_consensus", 0),
                "consensus_coverage": coverage,
                "last_generated_at": _now_utc().isoformat(),
            }
        )

        _runtime_state["last_donor_coverage_ratio"] = coverage
        if coverage < LOW_DONOR_COVERAGE_THRESHOLD:
            _runtime_state["low_donor_coverage_streak"] += 1
        else:
            _runtime_state["low_donor_coverage_streak"] = 0

    donor_summary.update(
        {
            "enabled": True,
            "catalog_total": len(catalog),
            "active_donors": len(active_catalog),
            "synthetic_enabled": EXTERNAL_DONOR_ENABLE_SYNTHETIC,
            "synthetic_signals_total": len(synthetic_signals),
            "json_feed_signals_total": len(json_feed_signals),
            "rss_feed_signals_total": len(rss_feed_signals),
            "text_feed_signals_total": len(text_feed_signals),
            "real_feed_signals_total": len(json_feed_signals) + len(rss_feed_signals) + len(text_feed_signals),
        }
    )
    return events, donor_summary, consensus_top

# ============================================
# ПОСТРОЕНИЕ ДАННЫХ
# ============================================

def _build_live_events(now_utc: datetime.datetime) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    for raw in _live_events_catalog():
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
    for tpl in _upcoming_event_templates():
        event_id, sport, league, home, away, offset_h, recs = tpl
        start_at = now_utc + datetime.timedelta(hours=float(offset_h))
        if start_at <= now_utc:
            continue
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


def _is_event_relevant_now(event: Dict[str, Any], now_utc: datetime.datetime, window_hours: int) -> bool:
    start_at = _parse_iso_datetime(event.get("start_at"))
    is_live = _safe_bool(event.get("is_live"), False)

    if start_at is None:
        return is_live

    if is_live:
        max_age = datetime.timedelta(hours=max(1.0, MAX_LIVE_EVENT_AGE_HOURS))
        if start_at > now_utc + datetime.timedelta(minutes=5):
            return False
        if start_at < now_utc - max_age:
            return False
        return True

    horizon = now_utc + datetime.timedelta(hours=max(1, window_hours))
    return now_utc <= start_at <= horizon


def _collect_raw_events(window_hours: int, include_live: bool, include_upcoming: bool) -> List[Dict[str, Any]]:
    now_utc = _now_utc()
    items: List[Dict[str, Any]] = []
    if include_live:
        items.extend(_build_live_events(now_utc))
    if include_upcoming:
        items.extend(_build_upcoming_events(now_utc, window_hours))

    return [
        event
        for event in items
        if _is_event_relevant_now(event, now_utc, window_hours)
    ]


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
    include_consensus: bool,
    min_consensus_sources: int,
    sort_by: str,
    limit: int,
    offset: int,
) -> Dict[str, Any]:
    raw_events = _collect_raw_events(window_hours, include_live, include_upcoming)
    prepared = [_prepare_event(e, min_probability, min_coefficient, min_support) for e in raw_events]

    if recommendations_only:
        prepared = [e for e in prepared if e.get("has_passable")]

    donor_summary: Dict[str, Any] = {"enabled": False}
    consensus_top: List[Dict[str, Any]] = []
    if include_consensus:
        prepared, donor_summary, consensus_top = _apply_external_consensus(
            prepared,
            min_sources=max(1, min_consensus_sources),
        )

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
            "include_consensus": include_consensus,
            "min_consensus_sources": max(1, min_consensus_sources),
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
            "events_with_external_consensus": donor_summary.get("events_with_consensus", 0),
            "consensus_coverage": donor_summary.get("consensus_coverage", 0.0),
        },
        "consensus_top": consensus_top,
        "external_donors": donor_summary,
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
        "external_consensus": event.get("external_consensus"),
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
    include_consensus: bool = True,
    min_consensus_sources: int = EXTERNAL_CONSENSUS_MIN_SOURCES,
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
        "include_consensus": _safe_bool(include_consensus, True),
        "min_consensus_sources": _coerce_int(min_consensus_sources, EXTERNAL_CONSENSUS_MIN_SOURCES, minimum=1, maximum=25),
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
        "include_consensus": _safe_bool(payload.get("include_consensus"), True),
        "min_consensus_sources": _coerce_int(payload.get("min_consensus_sources"), EXTERNAL_CONSENSUS_MIN_SOURCES, minimum=1, maximum=25),
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
            "include_consensus": _safe_bool(payload.get("include_consensus"), True),
            "min_consensus_sources": _coerce_int(payload.get("min_consensus_sources"), EXTERNAL_CONSENSUS_MIN_SOURCES, minimum=1, maximum=25),
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
        "include_consensus": True,
        "min_consensus_sources": EXTERNAL_CONSENSUS_MIN_SOURCES,
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
        "include_consensus": True,
        "min_consensus_sources": EXTERNAL_CONSENSUS_MIN_SOURCES,
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


@app.get("/api/consensus/top")
async def consensus_top(
    window_hours: int = DEFAULT_WINDOW_HOURS,
    include_live: bool = True,
    include_upcoming: bool = True,
    min_probability: float = DEFAULT_MIN_PROBABILITY,
    min_coefficient: float = DEFAULT_MIN_COEFFICIENT,
    min_bookmakers_support: float = DEFAULT_MIN_BOOKMAKERS_SUPPORT,
    min_consensus_sources: int = EXTERNAL_CONSENSUS_MIN_SOURCES,
    limit: int = 50,
    refresh: bool = False,
):
    params = {
        "window_hours": _coerce_int(window_hours, DEFAULT_WINDOW_HOURS, minimum=1, maximum=72),
        "include_live": _safe_bool(include_live, True),
        "include_upcoming": _safe_bool(include_upcoming, True),
        "min_probability": _coerce_float(min_probability, DEFAULT_MIN_PROBABILITY, minimum=0.0, maximum=1.0),
        "min_coefficient": _coerce_float(min_coefficient, DEFAULT_MIN_COEFFICIENT, minimum=1.0, maximum=50.0),
        "min_support": _coerce_float(min_bookmakers_support, DEFAULT_MIN_BOOKMAKERS_SUPPORT, minimum=0.0, maximum=20.0),
        "recommendations_only": False,
        "include_watch": True,
        "include_consensus": True,
        "min_consensus_sources": _coerce_int(min_consensus_sources, EXTERNAL_CONSENSUS_MIN_SOURCES, minimum=1, maximum=25),
        "sort_by": "passability",
        "limit": 500,
        "offset": 0,
    }

    entry = _storefront_cache_entry(params, refresh=_safe_bool(refresh, False))
    payload = entry.get("payload", {})
    min_sources = params["min_consensus_sources"]

    consensus_lines = [
        item
        for item in payload.get("consensus_top", [])
        if _coerce_int(item.get("donors_total"), 0) >= min_sources
    ]
    consensus_lines.sort(
        key=lambda item: (
            -_coerce_float(item.get("consensus_probability"), 0.0),
            -_coerce_float(item.get("agreement_score"), 0.0),
            -_coerce_int(item.get("donors_total"), 0),
        )
    )

    normalized_limit = _coerce_int(limit, 50, minimum=1, maximum=200)
    consensus_lines = consensus_lines[:normalized_limit]

    return {
        "total": len(consensus_lines),
        "items": consensus_lines,
        "filters": {
            "window_hours": params["window_hours"],
            "include_live": params["include_live"],
            "include_upcoming": params["include_upcoming"],
            "min_consensus_sources": min_sources,
            "limit": normalized_limit,
        },
        "external_donors": payload.get("external_donors", {}),
        "generated_at": payload.get("generated_at"),
    }


@app.get("/api/donors/status")
async def donors_status():
    catalog = _resolve_donor_catalog()
    json_feeds = _parse_external_feed_sources()
    rss_feeds = _parse_external_rss_sources()
    text_feeds = _parse_external_text_sources()
    with _metrics_lock:
        donor_pipeline = copy.deepcopy(_metrics.get("donor_pipeline", {}))
        runtime_snapshot = {
            "low_donor_coverage_streak": _runtime_state.get("low_donor_coverage_streak", 0),
            "last_donor_coverage_ratio": _runtime_state.get("last_donor_coverage_ratio", 0.0),
        }

    active = [item for item in catalog if item.get("active", True)]
    channels: Dict[str, int] = {}
    for item in active:
        channel = str(item.get("channel") or "external")
        channels[channel] = channels.get(channel, 0) + 1

    return {
        "enabled": _external_donors_active(),
        "ingestion_enabled": EXTERNAL_DONOR_INGESTION_ENABLED,
        "consensus_enabled": EXTERNAL_CONSENSUS_ENABLED,
        "catalog_total": len(catalog),
        "active_total": len(active),
        "channels": channels,
        "pipeline": donor_pipeline,
        "runtime": runtime_snapshot,
        "defaults": {
            "min_sources": EXTERNAL_CONSENSUS_MIN_SOURCES,
            "signal_limit_per_event": EXTERNAL_DONOR_SIGNAL_LIMIT_PER_EVENT,
            "donor_cache_ttl_seconds": DONOR_CACHE_TTL_SECONDS,
            "synthetic_enabled": EXTERNAL_DONOR_ENABLE_SYNTHETIC,
            "http_timeout_seconds": EXTERNAL_DONOR_HTTP_TIMEOUT_SECONDS,
            "http_max_body_bytes": EXTERNAL_DONOR_HTTP_MAX_BODY_BYTES,
            "rss_item_limit": EXTERNAL_DONOR_RSS_ITEM_LIMIT,
            "text_item_limit": EXTERNAL_DONOR_TEXT_ITEM_LIMIT,
            "pack_defaults_loaded": bool(_ENV_PACK_DEFAULTS),
        },
        "configured_feeds": {
            "json": len(json_feeds),
            "rss": len(rss_feeds),
            "text": len(text_feeds),
        },
        "sample_active_donors": active[:20],
        "timestamp": _now_utc().isoformat(),
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
            "donor_consensus_coverage": round(_coerce_float(metrics_snapshot.get("donor_pipeline", {}).get("consensus_coverage"), 0.0, minimum=0.0, maximum=1.0), 6),
            "donor_signals_total": _coerce_int(metrics_snapshot.get("donor_pipeline", {}).get("signals_total"), 0),
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
        low_donor_streak = _runtime_state.get("low_donor_coverage_streak", 0)
        donor_coverage = _runtime_state.get("last_donor_coverage_ratio", 0.0)
        donor_pipeline = copy.deepcopy(_metrics.get("donor_pipeline", {}))
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
            "max_live_event_age_hours": MAX_LIVE_EVENT_AGE_HOURS,
            "external_consensus_enabled": EXTERNAL_CONSENSUS_ENABLED,
            "external_consensus_min_sources": EXTERNAL_CONSENSUS_MIN_SOURCES,
            "external_donor_signal_limit_per_event": EXTERNAL_DONOR_SIGNAL_LIMIT_PER_EVENT,
            "external_donor_synthetic_enabled": EXTERNAL_DONOR_ENABLE_SYNTHETIC,
            "external_donor_http_timeout_seconds": EXTERNAL_DONOR_HTTP_TIMEOUT_SECONDS,
            "external_donor_http_max_body_bytes": EXTERNAL_DONOR_HTTP_MAX_BODY_BYTES,
            "external_donor_rss_item_limit": EXTERNAL_DONOR_RSS_ITEM_LIMIT,
            "external_donor_text_item_limit": EXTERNAL_DONOR_TEXT_ITEM_LIMIT,
                        "storefront_demo_events_enabled": STOREFRONT_DEMO_EVENTS_ENABLED,
            "storefront_events_source": "demo_templates" if STOREFRONT_DEMO_EVENTS_ENABLED else "none",
            "external_donor_ingestion_enabled": EXTERNAL_DONOR_INGESTION_ENABLED,
            "external_donor_pack_defaults_loaded": bool(_ENV_PACK_DEFAULTS),
        },
        "runtime": {
            "low_event_streak": low_streak,
            "last_storefront_total": _runtime_state["last_storefront_total"],
            "last_storefront_generated_at": _runtime_state["last_storefront_generated_at"],
            "low_donor_coverage_streak": low_donor_streak,
            "last_donor_coverage_ratio": donor_coverage,
        },
        "external_donors": donor_pipeline,
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
