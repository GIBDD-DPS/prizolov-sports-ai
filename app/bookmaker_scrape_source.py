# Bookmaker page scrape + external ingest cache for storefront events.

from __future__ import annotations

import datetime
import hashlib
import json
import logging
import os
import re
import threading
import time
from html import unescape
from typing import Any, Dict, List, Optional, Tuple
from urllib import parse as urllib_parse
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError

logger = logging.getLogger("PrizolovSportsAI.BookmakerScrape")

BOOKMAKER_SCRAPE_ENABLED = os.getenv("BOOKMAKER_SCRAPE_ENABLED", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
BOOKMAKER_SCRAPE_URLS = [
    part.strip()
    for part in (
        os.getenv("BOOKMAKER_SCRAPE_URLS")
        or "https://pari.ru/sports/football,https://pari.ru/live/football"
    ).split(",")
    if part.strip()
]
BOOKMAKER_SCRAPE_INTERVAL_SECONDS = int(os.getenv("BOOKMAKER_SCRAPE_INTERVAL_SECONDS", "300"))
BOOKMAKER_SCRAPE_CACHE_TTL_SECONDS = int(os.getenv("BOOKMAKER_SCRAPE_CACHE_TTL_SECONDS", "300"))
BOOKMAKER_SCRAPE_LIMIT = int(os.getenv("BOOKMAKER_SCRAPE_LIMIT", "60"))
BOOKMAKER_SCRAPE_USER_AGENT = (
    os.getenv("BOOKMAKER_SCRAPE_USER_AGENT")
    or "Mozilla/5.0 (compatible; Googlebot/2.1; +https://prizolov.ru/bot)"
).strip()
BOOKMAKER_INGEST_SECRET = (os.getenv("BOOKMAKER_INGEST_SECRET") or "").strip()

_cache_lock = threading.Lock()
_cache: Dict[str, Any] = {
    "ts": 0.0,
    "events": [],
    "source": "none",
    "last_error": None,
    "last_urls": [],
}

_TEAM_SPLIT_RE = re.compile(
    r"^(.{2,50}?)\s+(?:vs|v\.|—|–|-)\s+(.{2,50})$",
    re.IGNORECASE,
)


_PARI_MICRODATA_RE = re.compile(
    r'itemprop="homeTeam">([^<]{2,80})</div>\s*-\s*<div itemprop="awayTeam">([^<]{2,80})</div>',
    re.IGNORECASE,
)


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


def _format_event_time(value: Optional[str]) -> str:
    dt = _parse_iso_datetime(value)
    if not dt:
        return "—"
    return dt.strftime("%d.%m %H:%M UTC")


def _normalize_sport(raw: Optional[str]) -> str:
    value = (raw or "football").strip().lower()
    mapping = {
        "soccer": "football",
        "football": "football",
        "hockey": "hockey",
        "ice-hockey": "hockey",
        "basketball": "basketball",
        "tennis": "tennis",
        "volleyball": "volleyball",
        "esports": "esports",
        "cs": "esports",
    }
    return mapping.get(value, value or "other")


def _default_recommendations(now_utc: datetime.datetime) -> List[Dict[str, Any]]:
    return [
        {
            "line": "Исход: 1",
            "coefficient": 2.0,
            "probability": 0.62,
            "confidence": "med",
            "bookmakers_support": 2.5,
            "odds_updated_at": now_utc.isoformat(),
        }
    ]


def _event_from_teams(
    home: str,
    away: str,
    *,
    sport: str = "football",
    league: str = "Bookmaker line",
    is_live: bool = False,
    source_url: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    home = re.sub(r"\s+", " ", (home or "").strip())
    away = re.sub(r"\s+", " ", (away or "").strip())
    if len(home) < 2 or len(away) < 2:
        return None
    if home.lower() in away.lower() or away.lower() in home.lower():
        return None

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    event_id = hashlib.sha1(f"{home}|{away}|{league}|{sport}".encode("utf-8")).hexdigest()[:16]
    return {
        "id": f"bk_{event_id}",
        "sport": _normalize_sport(sport),
        "league": league,
        "home": home,
        "away": away,
        "status": "LIVE" if is_live else "UPCOMING",
        "time": "LIVE" if is_live else "—",
        "score": "—",
        "is_live": is_live,
        "start_at": now_utc.isoformat(),
        "source_url": source_url,
        "recommendations": _default_recommendations(now_utc),
    }


def _html_to_text(html: str) -> str:
    cleaned = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"<style[^>]*>.*?</style>", " ", cleaned, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    return unescape(re.sub(r"\s+", " ", cleaned))


def _extract_events_from_html(html: str, source_url: str) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    seen = set()

    sport_hint = "football"
    if "/hockey" in source_url:
        sport_hint = "hockey"
    elif "/tennis" in source_url:
        sport_hint = "tennis"
    elif "/basketball" in source_url:
        sport_hint = "basketball"
    elif "/esport" in source_url:
        sport_hint = "esports"
    is_live = "/live" in source_url

    for home, away in _PARI_MICRODATA_RE.findall(html):
        home = unescape(home).strip()
        away = unescape(away).strip()
        key = f"{home}|{away}"
        if key in seen:
            continue
        event = _event_from_teams(
            home,
            away,
            sport=sport_hint,
            league="Pari" if "pari.ru" in source_url else "Bookmaker",
            is_live=is_live,
            source_url=source_url,
        )
        if event:
            seen.add(key)
            events.append(event)

    for match in re.finditer(
        r">([A-Za-zА-Яа-я0-9][^<]{4,60}?)\s+(?:vs|v\.|—|–|-)\s+([A-Za-zА-Яа-я0-9][^<]{4,60})<",
        html,
        flags=re.IGNORECASE,
    ):
        home = unescape(match.group(1)).strip()
        away = unescape(match.group(2)).strip()
        key = f"{home}|{away}"
        if key in seen:
            continue
        event = _event_from_teams(
            home,
            away,
            sport=sport_hint,
            league="Pari" if "pari.ru" in source_url else "Bookmaker",
            is_live=is_live,
            source_url=source_url,
        )
        if event:
            seen.add(key)
            events.append(event)

    text = _html_to_text(html)
    for chunk in re.split(r"[|•·]", text):
        chunk = chunk.strip()
        split = _TEAM_SPLIT_RE.match(chunk)
        if not split:
            continue
        home, away = split.group(1).strip(), split.group(2).strip()
        key = f"{home}|{away}"
        if key in seen:
            continue
        event = _event_from_teams(
            home,
            away,
            sport=sport_hint,
            league="Pari" if "pari.ru" in source_url else "Bookmaker",
            is_live=is_live,
            source_url=source_url,
        )
        if event:
            seen.add(key)
            events.append(event)

    return events


def _fetch_url(url: str) -> Tuple[Optional[str], Optional[str]]:
    req = urllib_request.Request(
        url,
        headers={
            "User-Agent": BOOKMAKER_SCRAPE_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
        },
    )
    try:
        with urllib_request.urlopen(req, timeout=18) as response:
            body = response.read(2_500_000 + 1)
            if len(body) > 2_500_000:
                body = body[:2_500_000]
            charset = response.headers.get_content_charset() or "utf-8"
            return body.decode(charset, errors="ignore"), None
    except HTTPError as exc:
        return None, f"http_{exc.code}"
    except (URLError, TimeoutError, ValueError) as exc:
        return None, f"request_error:{exc}"


def scrape_bookmaker_urls_sync(urls: Optional[List[str]] = None, limit: int = BOOKMAKER_SCRAPE_LIMIT) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    if not BOOKMAKER_SCRAPE_ENABLED:
        return [], None

    targets = urls or BOOKMAKER_SCRAPE_URLS
    if not targets:
        return [], "bookmaker_no_urls"

    merged: List[Dict[str, Any]] = []
    seen_ids = set()
    last_error: Optional[str] = None

    for url in targets:
        html, err = _fetch_url(url)
        if err:
            last_error = f"bookmaker_{err}"
            logger.warning("Bookmaker scrape failed for %s: %s", url, err)
            continue
        if not html:
            continue
        for event in _extract_events_from_html(html, url):
            if event["id"] in seen_ids:
                continue
            seen_ids.add(event["id"])
            merged.append(event)
            if len(merged) >= limit:
                break
        if len(merged) >= limit:
            break

    if merged:
        return merged[:limit], None
    return [], last_error or "bookmaker_no_events_in_html"


def ingest_bookmaker_events(events: List[Dict[str, Any]]) -> int:
    normalized: List[Dict[str, Any]] = []
    now_utc = datetime.datetime.now(datetime.timezone.utc)

    for raw in events:
        if not isinstance(raw, dict):
            continue
        home = raw.get("home") or raw.get("home_team")
        away = raw.get("away") or raw.get("away_team")
        event = _event_from_teams(
            str(home or ""),
            str(away or ""),
            sport=str(raw.get("sport") or "football"),
            league=str(raw.get("league") or raw.get("tournament") or "Ingest"),
            is_live=bool(raw.get("is_live")),
            source_url=str(raw.get("source_url") or raw.get("url") or ""),
        )
        if not event:
            continue
        if raw.get("start_at"):
            event["start_at"] = raw.get("start_at")
            event["time"] = _format_event_time(raw.get("start_at"))
        if raw.get("recommendations") and isinstance(raw.get("recommendations"), list):
            event["recommendations"] = raw.get("recommendations")
        elif raw.get("coefficient") or raw.get("probability"):
            event["recommendations"] = [
                {
                    "line": str(raw.get("line") or "Исход: 1"),
                    "coefficient": float(raw.get("coefficient") or 1.8),
                    "probability": float(raw.get("probability") or 0.6),
                    "confidence": "med",
                    "bookmakers_support": 2.5,
                    "odds_updated_at": now_utc.isoformat(),
                }
            ]
        normalized.append(event)

    with _cache_lock:
        _cache["events"] = normalized[:BOOKMAKER_SCRAPE_LIMIT]
        _cache["ts"] = time.time()
        _cache["source"] = "bookmaker_ingest" if normalized else "none"
        _cache["last_error"] = None if normalized else "bookmaker_ingest_empty"

    return len(normalized)



_scrape_thread_started = False


def _ensure_background_scrape_started() -> None:
    global _scrape_thread_started
    if _scrape_thread_started or not BOOKMAKER_SCRAPE_ENABLED:
        return
    _scrape_thread_started = True

    def _loop() -> None:
        while BOOKMAKER_SCRAPE_ENABLED:
            try:
                scrape_bookmaker_urls_sync()
            except Exception as exc:
                logger.warning("Bookmaker background scrape error: %s", exc)
            time.sleep(max(60, BOOKMAKER_SCRAPE_INTERVAL_SECONDS))

    threading.Thread(target=_loop, name="bookmaker-scrape", daemon=True).start()
    logger.info(
        "Bookmaker background scrape started (interval=%ss, urls=%s)",
        BOOKMAKER_SCRAPE_INTERVAL_SECONDS,
        BOOKMAKER_SCRAPE_URLS,
    )


def get_cached_bookmaker_events(force_refresh: bool = False) -> List[Dict[str, Any]]:
    _ensure_background_scrape_started()
    now_ts = time.time()
    with _cache_lock:
        cached = list(_cache.get("events") or [])
        cached_ts = float(_cache.get("ts") or 0.0)
        if cached and not force_refresh and (now_ts - cached_ts) < BOOKMAKER_SCRAPE_CACHE_TTL_SECONDS:
            return cached

    if now_ts - cached_ts < BOOKMAKER_SCRAPE_INTERVAL_SECONDS and cached:
        return cached

    events, err = scrape_bookmaker_urls_sync()
    with _cache_lock:
        if events:
            _cache["events"] = events
            _cache["ts"] = now_ts
            _cache["source"] = "bookmaker_scrape"
            _cache["last_error"] = None
            _cache["last_urls"] = list(BOOKMAKER_SCRAPE_URLS)
        elif cached:
            return cached
        else:
            _cache["events"] = []
            _cache["ts"] = now_ts
            _cache["last_error"] = err
    return events


def get_status_snapshot() -> Dict[str, Any]:
    with _cache_lock:
        return {
            "enabled": BOOKMAKER_SCRAPE_ENABLED,
            "urls": list(BOOKMAKER_SCRAPE_URLS),
            "interval_seconds": BOOKMAKER_SCRAPE_INTERVAL_SECONDS,
            "cache_ttl_seconds": BOOKMAKER_SCRAPE_CACHE_TTL_SECONDS,
            "cached_events": len(_cache.get("events") or []),
            "source": _cache.get("source"),
            "last_error": _cache.get("last_error"),
            "ingest_configured": bool(BOOKMAKER_INGEST_SECRET),
        }
