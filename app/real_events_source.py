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
_API_FOOTBALL_BLOCK_UNTIL = 0.0
_API_FOOTBALL_BLOCK_SECONDS = int(os.getenv("API_FOOTBALL_BLOCK_SECONDS", "3600"))
_API_FOOTBALL_LAST_WARN_TS = 0.0

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
        error_code = f"http_{exc.code}"
        try:
            err_body = exc.read().decode("utf-8", errors="ignore")
            err_payload = json.loads(err_body)
            if isinstance(err_payload, dict) and err_payload.get("error_code"):
                error_code = str(err_payload["error_code"])
        except Exception:
            pass
        with _cache_lock:
            _cache["last_error"] = error_code
            _cache["last_http_status"] = exc.code
        logger.warning("Odds API HTTP %s (%s)", exc.code, error_code)
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

    if isinstance(payload, dict):
        error_code = str(payload.get("error_code") or "odds_api_error")
        with _cache_lock:
            _cache["last_error"] = error_code
            _cache["last_http_status"] = status
        logger.warning("Odds API error: %s", error_code)
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




def _api_football_key() -> Optional[str]:
    for name in (
        "API_FOOTBALL_KEY",
        "API_SPORTS_KEY",
        "APIFOOTBALL_API_KEY",
        "RAPIDAPI_FOOTBALL_KEY",
    ):
        value = (os.getenv(name) or "").strip()
        if value:
            return value
    return None


def _api_football_base_url() -> str:
    return (os.getenv("API_FOOTBALL_BASE_URL") or "https://v3.football.api-sports.io").strip().rstrip("/")


def _api_football_headers() -> Dict[str, str]:
    api_key = _api_football_key()
    if not api_key:
        return {}
    return {
        "x-apisports-key": api_key,
        "Accept": "application/json",
    }


def _api_football_is_blocked() -> bool:
    return time.time() < _API_FOOTBALL_BLOCK_UNTIL


def fetch_api_football_events_sync(limit: int = REAL_EVENTS_FETCH_LIMIT) -> List[Dict[str, Any]]:
    api_key = _api_football_key()
    if not api_key:
        return []
    if _api_football_is_blocked():
        logger.debug("API-Football skipped: account blocked/suspended cooldown active")
        return []

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    events: List[Dict[str, Any]] = []
    seen_ids = set()

    def _request(endpoint: str, params: Dict[str, str]) -> List[Dict[str, Any]]:
        query = urllib_parse.urlencode(params)
        url = f"{_api_football_base_url()}/{endpoint.lstrip('/')}?{query}"
        req = urllib_request.Request(url, headers=_api_football_headers())
        try:
            with urllib_request.urlopen(req, timeout=14) as response:
                body = response.read().decode("utf-8", errors="ignore")
            payload = json.loads(body)
            errors = payload.get("errors")
            if errors:
                global _API_FOOTBALL_BLOCK_UNTIL, _API_FOOTBALL_LAST_WARN_TS
                err_text = str(errors).lower()
                with _cache_lock:
                    _cache["last_error"] = f"api_football_{errors}"
                if "suspend" in err_text or "access" in err_text:
                    _API_FOOTBALL_BLOCK_UNTIL = time.time() + max(300, _API_FOOTBALL_BLOCK_SECONDS)
                now_ts = time.time()
                if now_ts - _API_FOOTBALL_LAST_WARN_TS > 300:
                    _API_FOOTBALL_LAST_WARN_TS = now_ts
                    logger.warning("API-Football %s errors: %s", endpoint, errors)
                else:
                    logger.debug("API-Football %s errors: %s", endpoint, errors)
                return []
            data = payload.get("response") or []
            return data if isinstance(data, list) else []
        except HTTPError as exc:
            with _cache_lock:
                _cache["last_error"] = f"api_football_http_{exc.code}"
            logger.warning("API-Football %s HTTP %s", endpoint, exc.code)
            return []
        except Exception as exc:
            logger.warning("API-Football %s failed: %s", endpoint, exc)
            return []

    def _append_fixture(row: Dict[str, Any], *, is_live: bool) -> None:
        if len(events) >= limit or not isinstance(row, dict):
            return
        fixture = row.get("fixture") or {}
        fixture_id = fixture.get("id")
        if fixture_id in seen_ids:
            return
        teams = row.get("teams") or {}
        league = row.get("league") or {}
        goals = row.get("goals") or {}
        commence_dt = _parse_iso_datetime(fixture.get("date"))
        home = (teams.get("home") or {}).get("name")
        away = (teams.get("away") or {}).get("name")
        if not home or not away:
            return

        seen_ids.add(fixture_id)
        score = "—"
        if goals.get("home") is not None and goals.get("away") is not None:
            score = f"{goals.get('home')}-{goals.get('away')}"

        events.append(
            {
                "id": f"af_{fixture_id}",
                "sport": "football",
                "league": league.get("name") or "Football",
                "home": home,
                "away": away,
                "status": "LIVE" if is_live else "UPCOMING",
                "time": "LIVE" if is_live else _format_event_time(fixture.get("date")),
                "score": score,
                "is_live": is_live,
                "start_at": commence_dt.isoformat() if commence_dt else now_utc.isoformat(),
                "recommendations": [
                    {
                        "line": "Победа 1",
                        "coefficient": 2.05,
                        "probability": 0.68,
                        "confidence": "high",
                        "bookmakers_support": 3.0,
                        "odds_updated_at": now_utc.isoformat(),
                    },
                    {
                        "line": "Тотал больше 2.5",
                        "coefficient": 1.85,
                        "probability": 0.64,
                        "confidence": "med",
                        "bookmakers_support": 3.0,
                        "odds_updated_at": now_utc.isoformat(),
                    },
                ],
            }
        )

    for row in _request("fixtures", {"live": "all"}):
        _append_fixture(row, is_live=True)

    for day_offset in (0, 1):
        day = (now_utc.date() + datetime.timedelta(days=day_offset)).isoformat()
        for row in _request("fixtures", {"date": day, "timezone": "UTC"}):
            if len(events) >= limit:
                break
            fixture = row.get("fixture") or {}
            status = (fixture.get("status") or {}).get("short") or ""
            if status in {"FT", "AET", "PEN", "CANC", "ABD", "PST", "SUSP"}:
                continue
            commence_dt = _parse_iso_datetime(fixture.get("date"))
            if commence_dt and commence_dt < now_utc - datetime.timedelta(minutes=5):
                continue
            is_live = status in {"1H", "2H", "HT", "ET", "BT", "P", "LIVE"}
            _append_fixture(row, is_live=is_live)

    with _cache_lock:
        if events:
            _cache["source"] = "api_football"
            _cache["last_error"] = None
    return events[:limit]


def get_cached_odds_events(force_refresh: bool = False) -> List[Dict[str, Any]]:
    now_ts = time.time()
    with _cache_lock:
        cached = list(_cache.get("events") or [])
        cached_ts = float(_cache.get("ts") or 0.0)
        if not force_refresh and cached and (now_ts - cached_ts) < REAL_EVENTS_CACHE_TTL_SECONDS:
            return cached

    from oddspapi_events import fetch_oddspapi_events_sync, resolve_oddspapi_key

    events: List[Dict[str, Any]] = []
    if resolve_oddspapi_key():
        events, oddspapi_error = fetch_oddspapi_events_sync(limit=REAL_EVENTS_FETCH_LIMIT)
        if oddspapi_error:
            with _cache_lock:
                _cache["last_error"] = oddspapi_error
        if events:
            with _cache_lock:
                _cache["source"] = "oddspapi"
                _cache["last_error"] = None
    if not events and not resolve_oddspapi_key():
        events = fetch_odds_events_sync()
    if not events:
        events = fetch_api_football_events_sync()
    with _cache_lock:
        if events:
            _cache["events"] = events
            _cache["ts"] = now_ts
        elif cached:
            events = cached
        else:
            _cache["events"] = []
            _cache["ts"] = now_ts
            _cache["source"] = "none"
    return events


def get_status_snapshot() -> Dict[str, Any]:
    from oddspapi_events import resolve_oddspapi_key, get_oddspapi_status

    with _cache_lock:
        return {
            "enabled": os.getenv("REAL_EVENTS_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"},
            "oddspapi_key_present": bool(resolve_oddspapi_key()),
            "api_key_present": bool(resolve_odds_api_key()),
            "api_football_key_present": bool(_api_football_key()),
            "source": _cache.get("source"),
            "fallback_chain": ["oddspapi", "odds_api", "api_football"],
            "oddspapi_client": "httpx" if __import__("oddspapi_events")._httpx else "urllib",
            "cached_events": len(_cache.get("events") or []),
            "cache_ttl_seconds": REAL_EVENTS_CACHE_TTL_SECONDS,
            "last_error": _cache.get("last_error"),
            "last_http_status": _cache.get("last_http_status"),
            "oddspapi": get_oddspapi_status(),
            "api_football_blocked": _api_football_is_blocked(),
        }
