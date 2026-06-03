# Winline.ru scrape probe (nearest/upcoming). HTTP page is SPA; line loads via WebSocket.

from __future__ import annotations

import logging
import os
import re
from html import unescape
from typing import Any, Dict, List, Optional, Tuple
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError

logger = logging.getLogger("PrizolovSportsAI.WinlineScrape")

WINLINE_NEAREST_URL = os.getenv("WINLINE_NEAREST_URL", "https://winline.ru/nearest").strip()
WINLINE_SCRAPE_ENABLED = os.getenv("WINLINE_SCRAPE_ENABLED", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
WINLINE_SCRAPE_USER_AGENT = (
    os.getenv("WINLINE_SCRAPE_USER_AGENT")
    or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
).strip()

_TEAM_PAIR_RE = re.compile(
    r">([A-Za-zА-Яа-я0-9][^<]{2,45}?)\s*(?:—|–|-|vs)\s*([A-Za-zА-Яа-я0-9][^<]{2,45})<",
    re.IGNORECASE,
)

_last_probe: Dict[str, Any] = {
    "last_error": None,
    "http_bytes": 0,
    "teams_found": 0,
    "websocket_required": True,
}


def _fetch_html(url: str) -> Tuple[Optional[str], Optional[str]]:
    req = urllib_request.Request(
        url,
        headers={
            "User-Agent": WINLINE_SCRAPE_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.9",
            "Referer": "https://winline.ru/",
        },
    )
    try:
        with urllib_request.urlopen(req, timeout=20) as response:
            body = response.read(1_500_000 + 1)
            if len(body) > 1_500_000:
                body = body[:1_500_000]
            charset = response.headers.get_content_charset() or "utf-8"
            return body.decode(charset, errors="ignore"), None
    except HTTPError as exc:
        return None, f"http_{exc.code}"
    except (URLError, TimeoutError, ValueError) as exc:
        return None, f"request_error:{exc}"


def probe_winline_nearest() -> Dict[str, Any]:
    """Check whether winline.ru/nearest exposes match data over plain HTTP."""
    global _last_probe
    html, err = _fetch_html(WINLINE_NEAREST_URL)
    if err:
        _last_probe = {
            "url": WINLINE_NEAREST_URL,
            "last_error": err,
            "http_bytes": 0,
            "teams_found": 0,
            "websocket_required": True,
            "feed_hint": "wss://wss.winline.ru/data_ng?client=newsite&nb=true",
        }
        return dict(_last_probe)

    teams = []
    for home, away in _TEAM_PAIR_RE.findall(html or ""):
        home = unescape(home).strip()
        away = unescape(away).strip()
        if len(home) >= 2 and len(away) >= 2:
            teams.append((home, away))

    has_app_shell = "main." in html and "polyfills." in html
    _last_probe = {
        "url": WINLINE_NEAREST_URL,
        "last_error": None if teams else "winline_spa_no_teams_in_html",
        "http_bytes": len(html or ""),
        "teams_found": len(teams),
        "websocket_required": has_app_shell and len(teams) == 0,
        "feed_hint": "wss://wss.winline.ru/data_ng?client=newsite&nb=true",
        "sample_teams": teams[:3],
    }
    return dict(_last_probe)


def scrape_winline_events_sync() -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Winline line is loaded via WebSocket after Angular bootstraps /nearest.
    Plain HTTP scrape returns no fixtures today.
    """
    if not WINLINE_SCRAPE_ENABLED:
        return [], None

    probe = probe_winline_nearest()
    if probe.get("teams_found", 0) > 0:
        logger.info("Winline HTTP probe found %s team pairs (unexpected)", probe["teams_found"])
        # Future: map teams to events when HTML SSR appears.
        return [], "winline_parser_not_implemented"

    err = probe.get("last_error") or "winline_websocket_feed_required"
    logger.info("Winline scrape skipped: %s (use WebSocket feed)", err)
    return [], err


def get_status_snapshot() -> Dict[str, Any]:
    return {
        "enabled": WINLINE_SCRAPE_ENABLED,
        "url": WINLINE_NEAREST_URL,
        "probe": dict(_last_probe),
    }
