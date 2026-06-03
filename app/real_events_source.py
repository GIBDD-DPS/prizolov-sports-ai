# Real storefront events from The Odds API (sync fetch for FastAPI storefront).

from __future__ import annotations

import datetime
import json
import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional
from urllib import parse as urllib_parse
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError

logger = logging.getLogger("PrizolovSportsAI.RealEvents")

ODDS_API_UPCOMING_URL = "https://api.the-odds-api.com/v4/sports/upcoming/odds/"
REAL_EVENTS_CACHE_TTL_SECONDS = int(os.getenv("REAL_EVENTS_CACHE_TTL_SECONDS", "90"))
REAL_EVENTS_FETCH_LIMIT = int(os.getenv("REAL_EVENTS_FETCH_LIMIT", "80"))

_cache_lock = threading.Lock()
_cache: Dict[str, Any] = {
    "ts": 0.0,
    "events": [],
    "source": "none",
    "last_error": None,
    "last_http_status": None,
}


def _parse_iso_datetime(value: Any) -> Optional[datetime.datetime]:
    if not value:
        return None
    try:
        raw = str(value).replace("Z", "+00:00")
        dt = datetime.datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt.astimezone(datetime.timezone.utc)
    except Exception:
        return None


def resolve_odds_api_key() -> Optional[str]:
    for name in ("THE_ODDS_API_KEY", "API_KEYS_ODDS", "ODDS_API_KEY"):
        value = (os.getenv(name) or "").strip()
        if value:
            return value
    return None


def _normalize_sport_key(sport_key: Optional[str]) -> str:
    raw = (sport_key or "").lower()
    if raw.startswith("soccer"):
        return "football"
    if raw.startswith("icehockey"):
        return "hockey"
    if raw.startswith("basketball"):
        return "basketball"
    if raw.startswith("tennis"):
        return "tennis"
    if raw.startswith("volleyball"):
        return "volleyball"
    if raw.startswith("mma"):
        return "mma"
    if raw.startswith("esports"):
        return "esports"
    if "_" in raw:
        return raw.split("_", 1)[0]
    return raw or "other"


def _format_event_time(commence_time: Optional[str]) -> str:
    dt = _parse_iso_datetime(commence_time)
    if not dt:
        return "—"
    return dt.strftime("%d.%m %H:%M UTC")


def _compute_probabilities(outcomes: List[Dict[str, Any]]) -> Dict[str, float]:
    valid = []
    for outcome in outcomes:
        try:
            price = float(outcome.get("price"))
        except (TypeError, ValueError):
            continue
        if price > 1.0:
            valid.append((str(outcome.get("name") or "Исход"), price))

    if not valid:
        return {}

    inv_values = [(name, 1.0 / price) for name, price in valid]
    inv_sum = sum(val for _, val in inv_values)
    if inv_sum <= 0:
        return {name: 0.0 for name, _ in valid}

    return {name: round(min(0.99, max(0.01, inv / inv_sum)), 4) for name, inv in inv_values}


def _extract_recommendations(
    event: Dict[str, Any],
    league: str,
    sport: str,
    home: str,
    away: str,
    bookmakers_count: int,
) -> List[Dict[str, Any]]:
    recommendations: List[Dict[str, Any]] = []
    bookmakers = event.get("bookmakers") or []
    if not isinstance(bookmakers, list):
        return recommendations

    chosen_market: Optional[Dict[str, Any]] = None
    for bookmaker in bookmakers:
        for market in bookmaker.get("markets") or []:
            if market.get("key") in {"h2h", "totals", "spreads"}:
                chosen_market = market
                break
        if chosen_market:
            break

    if not chosen_market:
        return recommendations

    outcomes = chosen_market.get("outcomes") or []
    if not isinstance(outcomes, list):
        return recommendations

    probabilities = _compute_probabilities(outcomes)
    market_key = chosen_market.get("key", "h2h")
    support = float(max(1, min(bookmakers_count, 12)))

    for outcome in outcomes[:4]:
        try:
            price = float(outcome.get("price"))
        except (TypeError, ValueError):
            continue
        if price <= 1.0:
            continue

        line_name = str(outcome.get("name") or "Исход")
        point = outcome.get("point")
        if point is not None:
            line_name = f"{line_name} {point}"

        name_key = str(outcome.get("name") or "Исход")
        probability = probabilities.get(name_key, round(min(0.99, 1.0 / price), 4))

        recommendations.append(
            {
                "league": league,
                "sport": sport,
                "home": home,
                "away": away,
                "line": line_name if market_key != "h2h" else f"{market_key.upper()}: {line_name}",
                "confidence": "high" if probability >= 0.45 else "med",
                "probability": probability,
                "coefficient": round(price, 2),
                "bookmakers_support": support,
            }
        )

    return recommendations


def transform_odds_event(event: Dict[str, Any], now_utc: datetime.datetime) -> Optional[Dict[str, Any]]:
    home = event.get("home_team")
    away = event.get("away_team")
    if not home or not away:
        return None

    sport = _normalize_sport_key(event.get("sport_key"))
    league = event.get("sport_title") or event.get("sport_key") or "Unknown League"
    commence_time = event.get("commence_time")
    commence_dt = _parse_iso_datetime(commence_time)

    is_live = bool(commence_dt and commence_dt <= now_utc)
    status = "LIVE" if is_live else "UPCOMING"
    bookmakers_count = len(event.get("bookmakers") or [])

    recommendations = _extract_recommendations(event, league, sport, home, away, bookmakers_count)
    if not recommendations:
        return None

    return {
        "id": str(event.get("id") or f"{sport}_{home}_{away}"),
        "sport": sport,
        "league": league,
        "home": home,
        "away": away,
        "status": status,
        "time": "LIVE" if is_live else _format_event_time(commence_time),
        "score": "—",
        "is_live": is_live,
        "start_at": commence_dt.isoformat() if commence_dt else None,
        "recommendations": recommendations,
    }


def fetch_odds_events_sync(limit: int = REAL_EVENTS_FETCH_LIMIT) -> List[Dict[str, Any]]:
    api_key = resolve_odds_api_key()
    if not api_key:
        with _cache_lock:
            _cache["last_error"] = "missing_api_key"
            _cache["last_http_status"] = None
        logger.warning("THE_ODDS_API_KEY не задан — реальные события недоступны")
        return []

    params = urllib_parse.urlencode(
        {
            "apiKey": api_key,
            "regions": "eu,uk",
            "markets": "h2h,totals",
            "oddsFormat": "decimal",
            "dateFormat": "iso",
        }
    )
    url = f"{ODDS_API_UPCOMING_URL}?{params}"

    try:
        with urllib_request.urlopen(url, timeout=12) as response:
            status = getattr(response, "status", 200)
            body = response.read().decode("utf-8", errors="ignore")
    except HTTPError as exc:
        with _cache_lock:
            _cache["last_error"] = f"http_{exc.code}"
            _cache["last_http_status"] = exc.code
        logger.warning("Odds API HTTP %s", exc.code)
        return []
    except (URLError, TimeoutError, ValueError) as exc:
        with _cache_lock:
            _cache["last_error"] = f"request_error: {exc}"
            _cache["last_http_status"] = None
        logger.warning("Odds API request failed: %s", exc)
        return []

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        with _cache_lock:
            _cache["last_error"] = "invalid_json"
            _cache["last_http_status"] = status
        return []

    if not isinstance(payload, list):
        with _cache_lock:
            _cache["last_error"] = "invalid_payload"
            _cache["last_http_status"] = status
        return []

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    events: List[Dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        transformed = transform_odds_event(item, now_utc)
        if transformed:
            events.append(transformed)

    events.sort(
        key=lambda ev: (
            not ev.get("is_live"),
            ev.get("start_at") or "",
        )
    )
    result = events[: max(1, limit)]

    with _cache_lock:
        _cache["last_error"] = None
        _cache["last_http_status"] = status
        _cache["source"] = "odds_api"

    return result


def get_cached_odds_events(force_refresh: bool = False) -> List[Dict[str, Any]]:
    now_ts = time.time()
    with _cache_lock:
        cached = list(_cache.get("events") or [])
        cached_ts = float(_cache.get("ts") or 0.0)
        if not force_refresh and cached and (now_ts - cached_ts) < REAL_EVENTS_CACHE_TTL_SECONDS:
            return cached

    events = fetch_odds_events_sync()
    with _cache_lock:
        _cache["events"] = events
        _cache["ts"] = now_ts
        if not events and _cache.get("source") != "odds_api":
            _cache["source"] = "none"
    return events


def get_status_snapshot() -> Dict[str, Any]:
    with _cache_lock:
        return {
            "enabled": os.getenv("REAL_EVENTS_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"},
            "api_key_present": bool(resolve_odds_api_key()),
            "source": _cache.get("source"),
            "cached_events": len(_cache.get("events") or []),
            "cache_ttl_seconds": REAL_EVENTS_CACHE_TTL_SECONDS,
            "last_error": _cache.get("last_error"),
            "last_http_status": _cache.get("last_http_status"),
        }
