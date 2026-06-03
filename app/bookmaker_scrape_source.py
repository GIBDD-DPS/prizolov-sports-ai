# Bookmaker page scrape + external ingest cache for storefront events.

from __future__ import annotations

import datetime
import hashlib
import logging
import os
import re
import threading
import time
from html import unescape
from typing import Any, Dict, List, Optional, Tuple
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError

logger = logging.getLogger("PrizolovSportsAI.BookmakerScrape")


def _is_truthy_env(name: str) -> bool:
    return (os.getenv(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def _bookmaker_scrape_enabled_from_env() -> bool:
    """Explicit BOOKMAKER_SCRAPE_ENABLED wins; on Amvera default to enabled."""
    explicit = os.getenv("BOOKMAKER_SCRAPE_ENABLED")
    if explicit is not None and explicit.strip() != "":
        return _is_truthy_env("BOOKMAKER_SCRAPE_ENABLED")
    return _is_truthy_env("AMVERA")


BOOKMAKER_SCRAPE_ENABLED = _bookmaker_scrape_enabled_from_env()
BOOKMAKER_SCRAPE_URLS = [
    part.strip()
    for part in (
        os.getenv("BOOKMAKER_SCRAPE_URLS")
        or ",".join(
            [
                "https://pari.ru/live?dateInterval=5",
                "https://pari.ru/sports/football?dateInterval=5",
                "https://pari.ru/sports/hockey?dateInterval=5",
                "https://pari.ru/sports/basketball?dateInterval=5",
                "https://pari.ru/sports/tennis?dateInterval=5",
            ]
        )
    ).split(",")
    if part.strip()
]
BOOKMAKER_SCRAPE_INTERVAL_SECONDS = int(os.getenv("BOOKMAKER_SCRAPE_INTERVAL_SECONDS", "300"))
BOOKMAKER_SCRAPE_CACHE_TTL_SECONDS = int(os.getenv("BOOKMAKER_SCRAPE_CACHE_TTL_SECONDS", "300"))
BOOKMAKER_SCRAPE_LIMIT = int(os.getenv("BOOKMAKER_SCRAPE_LIMIT", "80"))
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

_PARI_TEAM_RE = re.compile(
    r'itemprop="homeTeam">([^<]{2,80})</div>\s*-\s*<div itemprop="awayTeam">([^<]{2,80})</div>',
    re.IGNORECASE,
)
_PARI_SCORE_RE = re.compile(r'event-block-score[^"]*">([^<]+)</div>', re.IGNORECASE)
_PARI_MINUTE_RE = re.compile(r'event-block-current-time__time[^"]*">([^<]+)</div>', re.IGNORECASE)
_PARI_LEAGUE_RE = re.compile(r'itemprop="description" content="([^"]+)"', re.IGNORECASE)
_PARI_SPORT_RE = re.compile(r'itemprop="sport" content="([^"]+)"', re.IGNORECASE)
_PARI_START_RE = re.compile(r'itemprop="startDate" content="([^"]+)"', re.IGNORECASE)
_ODDS_RE = re.compile(r">([1-9]\.[0-9]{2})</")


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


def _normalize_sport(raw: Optional[str], source_url: str = "") -> str:
    value = (raw or "").strip().lower()
    mapping = {
        "футбол": "football",
        "soccer": "football",
        "football": "football",
        "хоккей": "hockey",
        "hockey": "hockey",
        "ice-hockey": "hockey",
        "баскетбол": "basketball",
        "basketball": "basketball",
        "теннис": "tennis",
        "tennis": "tennis",
        "волейбол": "volleyball",
        "volleyball": "volleyball",
        "киберспорт": "esports",
        "esports": "esports",
    }
    if value in mapping:
        return mapping[value]
    url = source_url.lower()
    if "/hockey" in url:
        return "hockey"
    if "/basketball" in url:
        return "basketball"
    if "/tennis" in url:
        return "tennis"
    if "/esport" in url:
        return "esports"
    return mapping.get(value, value or "football")


def _extract_odds(chunk: str, limit: int = 8) -> List[float]:
    odds: List[float] = []
    for match in _ODDS_RE.finditer(chunk):
        try:
            value = float(match.group(1))
        except ValueError:
            continue
        if 1.01 <= value <= 100.0:
            odds.append(value)
        if len(odds) >= limit:
            break
    return odds


def _recommendations_from_odds(
    home: str,
    away: str,
    odds: List[float],
    now_utc: datetime.datetime,
) -> List[Dict[str, Any]]:
    if len(odds) < 3:
        return []

    markets = [
        (f"Победа {home}", odds[0]),
        ("Ничья", odds[1]),
        (f"Победа {away}", odds[2]),
    ]
    inv_sum = sum(1.0 / coef for _, coef in markets)
    if inv_sum <= 0:
        return []

    recommendations: List[Dict[str, Any]] = []
    for line, coefficient in markets:
        implied = (1.0 / coefficient) / inv_sum
        probability = min(0.97, max(0.05, implied * 0.97))
        confidence = "high" if probability >= 0.68 else "med"
        recommendations.append(
            {
                "line": line,
                "coefficient": round(coefficient, 2),
                "probability": round(probability, 4),
                "confidence": confidence,
                "bookmakers_support": 3.0,
                "odds_updated_at": now_utc.isoformat(),
            }
        )

    recommendations.sort(key=lambda item: (-item["probability"], -item["coefficient"]))
    return recommendations


def _build_event(
    *,
    home: str,
    away: str,
    sport: str,
    league: str,
    is_live: bool,
    score: str,
    live_minute: str,
    start_at: Optional[str],
    source_url: str,
    recommendations: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    home = re.sub(r"\s+", " ", (home or "").strip())
    away = re.sub(r"\s+", " ", (away or "").strip())
    if len(home) < 2 or len(away) < 2:
        return None
    if home.lower() in away.lower() or away.lower() in home.lower():
        return None
    if not recommendations:
        return None

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    start_dt = _parse_iso_datetime(start_at)
    if not start_dt:
        start_dt = now_utc if is_live else now_utc + datetime.timedelta(hours=2)

    if is_live:
        time_label = live_minute or "LIVE"
        status = "LIVE"
    else:
        time_label = _format_event_time(start_dt.isoformat())
        status = "UPCOMING"

    event_id = hashlib.sha1(f"{home}|{away}|{league}|{sport}".encode("utf-8")).hexdigest()[:16]
    return {
        "id": f"bk_{event_id}",
        "sport": sport,
        "league": league,
        "home": home,
        "away": away,
        "status": status,
        "time": time_label,
        "live_minute": live_minute or "",
        "score": score or "—",
        "is_live": is_live,
        "start_at": start_dt.isoformat(),
        "source_url": source_url,
        "recommendations": recommendations,
    }


def _sport_hint_from_url(source_url: str) -> str:
    url = source_url.lower()
    if "/hockey" in url:
        return "hockey"
    if "/basketball" in url:
        return "basketball"
    if "/tennis" in url:
        return "tennis"
    if "/esport" in url:
        return "esports"
    return "football"


def _extract_pari_events_from_html(html: str, source_url: str) -> List[Dict[str, Any]]:
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    sport_hint = _sport_hint_from_url(source_url)
    by_key: Dict[str, Dict[str, Any]] = {}

    for match in _PARI_TEAM_RE.finditer(html):
        home = unescape(match.group(1)).strip()
        away = unescape(match.group(2)).strip()
        chunk = html[match.start() : match.start() + 2800]

        score_match = _PARI_SCORE_RE.search(chunk)
        minute_match = _PARI_MINUTE_RE.search(chunk)
        league_match = _PARI_LEAGUE_RE.search(chunk)
        sport_match = _PARI_SPORT_RE.search(chunk)
        start_match = _PARI_START_RE.search(chunk)

        is_live = minute_match is not None
        live_minute = minute_match.group(1).strip() if minute_match else ""
        score = score_match.group(1).strip() if score_match else "—"
        league = league_match.group(1).strip() if league_match else "Линия букмекера"
        sport = _normalize_sport(sport_match.group(1) if sport_match else sport_hint, source_url)
        start_at = start_match.group(1).strip() if start_match else None

        odds = _extract_odds(chunk)
        recommendations = _recommendations_from_odds(home, away, odds, now_utc)
        if not recommendations:
            continue

        event = _build_event(
            home=home,
            away=away,
            sport=sport,
            league=league,
            is_live=is_live,
            score=score,
            live_minute=live_minute,
            start_at=start_at,
            source_url=source_url,
            recommendations=recommendations,
        )
        if not event:
            continue

        dedupe_key = f"{home}|{away}|{sport}"
        existing = by_key.get(dedupe_key)
        if existing is None:
            by_key[dedupe_key] = event
        elif event.get("is_live") and not existing.get("is_live"):
            by_key[dedupe_key] = event

    return list(by_key.values())


def _extract_events_from_html(html: str, source_url: str) -> List[Dict[str, Any]]:
    if "pari.ru" in source_url:
        return _extract_pari_events_from_html(html, source_url)
    return []


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
    for raw in events:
        if isinstance(raw, dict) and raw.get("home") and raw.get("away") and raw.get("recommendations"):
            normalized.append(raw)
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
