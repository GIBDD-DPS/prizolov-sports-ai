# Melbet.ru sport calendar probe and optional GetEvents API ingest.
# Calendar: https://melbet.ru/ru/sport/calendar?filter=e30=  (filter e30= is base64 "{}" = all sports)

from __future__ import annotations

import base64
import datetime
import hashlib
import json
import logging
import os
import re
from html import unescape
from typing import Any, Dict, List, Optional, Tuple
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError

logger = logging.getLogger("PrizolovSportsAI.MelbetScrape")

MELBET_CALENDAR_URL = (
    os.getenv("MELBET_CALENDAR_URL", "https://melbet.ru/ru/sport/calendar?filter=e30=").strip()
)
MELBET_SCRAPE_ENABLED = os.getenv("MELBET_SCRAPE_ENABLED", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
MELBET_SPORTS_API_BASE = (os.getenv("MELBET_SPORTS_API_BASE") or "").strip().rstrip("/")
MELBET_API_TOKEN = (os.getenv("MELBET_API_TOKEN") or "").strip()
MELBET_API_LANGUAGE = (os.getenv("MELBET_API_LANGUAGE") or "ru").strip()
MELBET_SCRAPE_USER_AGENT = (
    os.getenv("MELBET_SCRAPE_USER_AGENT")
    or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
).strip()

# sportType ids from Melbet/1xBet-style sports API (see docs/melbet-calendar.md)
MELBET_SPORT_TYPES: Dict[int, str] = {
    1: "football",
    2: "basketball",
    3: "american_football",
    4: "hockey",
    5: "tennis",
    6: "volleyball",
    7: "handball",
    8: "baseball",
    9: "badminton",
    10: "table_tennis",
    11: "boxing",
    12: "cricket",
    13: "darts",
    14: "rugby",
    16: "futsal",
    24: "handball",
    26: "rugby",
    43: "esports",
}

_TEAM_JSON_RE = re.compile(
    r'"homeName"\s*:\s*"([^"\\]+)".{0,400}?"awayName"\s*:\s*"([^"\\]+)"',
    re.DOTALL,
)

_last_probe: Dict[str, Any] = {
    "last_error": None,
    "http_bytes": 0,
    "teams_found": 0,
    "geo_blocked": False,
}


def decode_calendar_filter(filter_b64: str = "e30=") -> Any:
    """Melbet calendar ?filter= is base64 JSON, e.g. e30= -> {} (all sports)."""
    try:
        padded = filter_b64 + "=" * (-len(filter_b64) % 4)
        raw = base64.urlsafe_b64decode(padded.encode("ascii"))
        return json.loads(raw.decode("utf-8"))
    except (ValueError, json.JSONDecodeError):
        return None


def _fetch(url: str, *, json_accept: bool = False) -> Tuple[Optional[str], Optional[str]]:
    headers = {
        "User-Agent": MELBET_SCRAPE_USER_AGENT,
        "Accept-Language": "ru-RU,ru;q=0.9",
        "Referer": "https://melbet.ru/",
    }
    if json_accept:
        headers["Accept"] = "application/json"
    else:
        headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    if MELBET_API_TOKEN:
        headers["Authorization"] = f"Bearer {MELBET_API_TOKEN}"

    req = urllib_request.Request(url, headers=headers)
    try:
        with urllib_request.urlopen(req, timeout=20) as response:
            body = response.read(2_000_000 + 1)
            if len(body) > 2_000_000:
                body = body[:2_000_000]
            charset = response.headers.get_content_charset() or "utf-8"
            return body.decode(charset, errors="ignore"), None
    except HTTPError as exc:
        return None, f"http_{exc.code}"
    except (URLError, TimeoutError, ValueError) as exc:
        return None, f"request_error:{exc}"


def probe_melbet_calendar() -> Dict[str, Any]:
    """Check if Melbet calendar HTML is reachable (geo/VPN block is common off-RU)."""
    global _last_probe
    html, err = _fetch(MELBET_CALENDAR_URL)
    if err:
        _last_probe = {
            "url": MELBET_CALENDAR_URL,
            "last_error": err,
            "http_bytes": 0,
            "teams_found": 0,
            "geo_blocked": err == "http_403",
            "calendar_filter_decoded": decode_calendar_filter("e30="),
        }
        return dict(_last_probe)

    geo_blocked = "недоступен" in (html or "").lower() or "site-unavailable" in (html or "")
    teams: List[Tuple[str, str]] = []
    for home, away in _TEAM_JSON_RE.findall(html or ""):
        home = unescape(home).strip()
        away = unescape(away).strip()
        if len(home) >= 2 and len(away) >= 2:
            teams.append((home, away))

    _last_probe = {
        "url": MELBET_CALENDAR_URL,
        "last_error": None if teams else ("melbet_geo_or_spa" if geo_blocked else "melbet_no_teams_in_html"),
        "http_bytes": len(html or ""),
        "teams_found": len(teams),
        "geo_blocked": geo_blocked,
        "calendar_filter_decoded": decode_calendar_filter("e30="),
        "sample_teams": teams[:3],
        "api_configured": bool(MELBET_SPORTS_API_BASE and MELBET_API_TOKEN),
    }
    return dict(_last_probe)


def _fetch_api_events_for_sport(sport_type: int, limit: int) -> List[Dict[str, Any]]:
    if not MELBET_SPORTS_API_BASE or not MELBET_API_TOKEN:
        return []

    version = os.getenv("MELBET_SPORTS_API_VERSION", "v1").strip() or "v1"
    query = f"$filter=sporttype eq {sport_type}"
    url = (
        f"{MELBET_SPORTS_API_BASE}/sports/{version}/GetEvents"
        f"?query={urllib_request.quote(query)}&includeMarkets=none&language={MELBET_API_LANGUAGE}"
    )
    body, err = _fetch(url, json_accept=True)
    if err or not body:
        logger.warning("Melbet API sport %s failed: %s", sport_type, err)
        return []

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        logger.warning("Melbet API sport %s returned non-JSON", sport_type)
        return []

    events_raw = payload.get("events") or []
    sport_key = MELBET_SPORT_TYPES.get(sport_type, "other")
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    out: List[Dict[str, Any]] = []

    for item in events_raw[:limit]:
        if not isinstance(item, dict):
            continue
        team = item.get("teamInfo") or {}
        home = str(team.get("homeName") or "").strip()
        away = str(team.get("awayName") or "").strip()
        if len(home) < 2 or len(away) < 2:
            continue
        league = str(item.get("leagueName") or "Melbet").strip()
        is_live = bool(item.get("isLive"))
        game = item.get("gameInfo") or {}
        score = "—"
        if is_live:
            hs = game.get("liveHomeScore")
            aws = game.get("liveAwayScore")
            if hs is not None and aws is not None:
                score = f"{hs}:{aws}"

        kickoff = item.get("globalShowTime") or item.get("kickOffTime")
        start_at = kickoff if isinstance(kickoff, str) else None

        event_id = hashlib.sha1(f"melbet|{home}|{away}|{sport_key}".encode()).hexdigest()[:16]
        out.append(
            {
                "id": f"melbet_{event_id}",
                "sport": sport_key,
                "league": league,
                "home": home,
                "away": away,
                "status": "LIVE" if is_live else "UPCOMING",
                "time": "LIVE" if is_live else "Скоро",
                "live_minute": "",
                "score": score,
                "is_live": is_live,
                "start_at": start_at or now_utc.isoformat(),
                "source_url": MELBET_CALENDAR_URL,
                "recommendations": [
                    {
                        "line": f"Матч · Победа {home} (основной рынок Melbet)",
                        "coefficient": 1.85,
                        "probability": 0.54,
                        "confidence": "med",
                        "bookmakers_support": 2.0,
                        "market_scope": "Матч",
                        "line_detail": f"Событие из календаря Melbet, вид спорта: {sport_key}.",
                        "odds_updated_at": now_utc.isoformat(),
                    }
                ],
            }
        )
    return out


def _events_from_calendar_html(limit: int) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    html, err = _fetch(MELBET_CALENDAR_URL)
    if err:
        return [], f"melbet_{err}"
    if not html or "site-unavailable" in html:
        return [], "melbet_geo_blocked"

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    seen = set()
    events: List[Dict[str, Any]] = []
    for home, away in _TEAM_JSON_RE.findall(html):
        home = unescape(home).strip()
        away = unescape(away).strip()
        key = f"{home}|{away}"
        if key in seen:
            continue
        seen.add(key)
        event_id = hashlib.sha1(f"melbet_html|{key}".encode()).hexdigest()[:16]
        events.append(
            {
                "id": f"melbet_{event_id}",
                "sport": "football",
                "league": "Melbet",
                "home": home,
                "away": away,
                "status": "UPCOMING",
                "time": "Скоро",
                "live_minute": "",
                "score": "—",
                "is_live": False,
                "start_at": now_utc.isoformat(),
                "source_url": MELBET_CALENDAR_URL,
                "recommendations": [
                    {
                        "line": f"Матч · {home} vs {away} (календарь Melbet)",
                        "coefficient": 1.80,
                        "probability": 0.55,
                        "confidence": "med",
                        "bookmakers_support": 2.0,
                        "market_scope": "Матч",
                        "line_detail": "Данные со страницы календаря Melbet (без коэффициентов в HTML).",
                        "odds_updated_at": now_utc.isoformat(),
                    }
                ],
            }
        )
        if len(events) >= limit:
            break
    if events:
        return events, None
    return [], "melbet_calendar_no_events_in_html"


def scrape_melbet_events_sync(limit: int = 40) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    if not MELBET_SCRAPE_ENABLED:
        return [], None

    merged: List[Dict[str, Any]] = []
    last_error: Optional[str] = None

    if MELBET_SPORTS_API_BASE and MELBET_API_TOKEN:
        per_sport = max(3, limit // max(len(MELBET_SPORT_TYPES), 1))
        for sport_type in MELBET_SPORT_TYPES:
            merged.extend(_fetch_api_events_for_sport(sport_type, per_sport))
            if len(merged) >= limit:
                break

    if len(merged) < limit:
        html_events, html_err = _events_from_calendar_html(limit - len(merged))
        if html_events:
            merged.extend(html_events)
        elif html_err:
            last_error = html_err

    if merged:
        return merged[:limit], None
    probe_melbet_calendar()
    return [], last_error or _last_probe.get("last_error") or "melbet_no_events"


def get_status_snapshot() -> Dict[str, Any]:
    probe = probe_melbet_calendar() if MELBET_SCRAPE_ENABLED else {}
    return {
        "enabled": MELBET_SCRAPE_ENABLED,
        "calendar_url": MELBET_CALENDAR_URL,
        "calendar_filter_decoded": decode_calendar_filter("e30="),
        "sport_types_supported": MELBET_SPORT_TYPES,
        "api_configured": bool(MELBET_SPORTS_API_BASE and MELBET_API_TOKEN),
        "api_base": MELBET_SPORTS_API_BASE or None,
        "probe": probe,
        "note": "Календарь Melbet: filter=e30= это {} (все виды спорта). Нужен RU IP или JWT API.",
    }
