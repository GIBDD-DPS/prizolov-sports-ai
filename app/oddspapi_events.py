# OddsPapi storefront events (https://oddspapi.io/)

from __future__ import annotations

import datetime
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib import parse as urllib_parse
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError

logger = logging.getLogger("PrizolovSportsAI.OddsPapi")

ODDSPAPI_BASE_URL = "https://api.oddspapi.io/v4"
ODDSPAPI_BOOKMAKER = (os.getenv("ODDSPAPI_BOOKMAKER") or "pinnacle").strip()
ODDSPAPI_USER_AGENT = (os.getenv("ODDSPAPI_USER_AGENT") or "PrizolovSportsAI/14.0 (+https://prizolov.ru)").strip()
ODDSPAPI_SPORT_IDS = [
    int(part)
    for part in (os.getenv("ODDSPAPI_SPORT_IDS") or "10").split(",")
    if part.strip().isdigit()
]
ODDSPAPI_MAX_TOURNAMENTS_PER_REQUEST = min(5, int(os.getenv("ODDSPAPI_MAX_TOURNAMENTS_PER_REQUEST", "5")))
ODDSPAPI_FIXTURE_HORIZON_HOURS = int(os.getenv("ODDSPAPI_FIXTURE_HORIZON_HOURS", "72"))
ODDSPAPI_PRIORITY_MARKETS = ("101", "104", "1010")
ODDSPAPI_REQUEST_PAUSE_SECONDS = float(os.getenv("ODDSPAPI_REQUEST_PAUSE_SECONDS", "0.55"))

ODDSPAPI_SPORT_ID_TO_KEY = {
    10: "football",
    11: "basketball",
    15: "hockey",
    12: "tennis",
    23: "volleyball",
}

ODDSPAPI_OUTCOME_LABELS: Dict[str, Dict[str, str]] = {
    "101": {"101": "Победа 1", "102": "Ничья", "103": "Победа 2"},
    "104": {"104": "Обе забьют — ДА", "105": "Обе забьют — НЕТ"},
    "1010": {"1010": "Тотал больше 2.5", "1011": "Тотал меньше 2.5"},
}

_RATE_LIMITED = {"__oddspapi_rate_limited__": True}


def resolve_oddspapi_key() -> Optional[str]:
    for name in ("ODDSPAPI_API_KEY", "API_KEYS_ODDSPAPI", "ODDS_PAPI_API_KEY"):
        value = (os.getenv(name) or "").strip()
        if value:
            return value
    return None


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


def _oddspapi_get(endpoint: str, params: Dict[str, Any]) -> Tuple[Any, Optional[str]]:
    api_key = resolve_oddspapi_key()
    if not api_key:
        return None, "missing_api_key"

    query = dict(params)
    query["apiKey"] = api_key
    url = f"{ODDSPAPI_BASE_URL}/{endpoint.lstrip('/')}?{urllib_parse.urlencode(query)}"
    req = urllib_request.Request(url, headers={"User-Agent": ODDSPAPI_USER_AGENT, "Accept": "application/json"})

    last_error: Optional[str] = None
    for attempt in range(2):
        try:
            with urllib_request.urlopen(req, timeout=14) as response:
                status = getattr(response, "status", 200)
                body = response.read().decode("utf-8", errors="ignore")
        except HTTPError as exc:
            error_code = f"http_{exc.code}"
            try:
                err_body = exc.read().decode("utf-8", errors="ignore")
                err_payload = json.loads(err_body)
                if isinstance(err_payload, dict):
                    err_obj = err_payload.get("error") if isinstance(err_payload.get("error"), dict) else err_payload
                    error_code = str(
                        err_payload.get("error_code")
                        or (err_obj or {}).get("code")
                        or (err_obj or {}).get("message")
                        or error_code
                    )
            except Exception:
                pass
            last_error = f"oddspapi_{error_code}"
            if exc.code == 429 and attempt == 0:
                logger.warning("OddsPapi rate limited, retrying in 2s")
                time.sleep(2.0)
                continue
            logger.warning("OddsPapi HTTP %s (%s)", exc.code, error_code)
            if exc.code == 429:
                return _RATE_LIMITED, last_error
            return None, last_error
        except (URLError, TimeoutError, ValueError) as exc:
            logger.warning("OddsPapi request failed: %s", exc)
            return None, f"oddspapi_request_error: {exc}"

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return None, "oddspapi_invalid_json"

        if isinstance(payload, dict) and payload.get("error"):
            err_obj = payload.get("error")
            code = err_obj.get("code") if isinstance(err_obj, dict) else payload.get("error")
            return None, f"oddspapi_{code}"

        if status >= 400:
            return None, f"oddspapi_http_{status}"

        return payload, None

    return _RATE_LIMITED, last_error or "oddspapi_RATE_LIMITED"



def _oddspapi_normalize_sport(sport_id: Any) -> str:
    try:
        sid = int(sport_id)
    except (TypeError, ValueError):
        return "other"
    return ODDSPAPI_SPORT_ID_TO_KEY.get(sid, "other")


def _oddspapi_market_outcomes(markets: Dict[str, Any], market_id: str) -> List[Dict[str, Any]]:
    market = markets.get(str(market_id)) or markets.get(market_id)
    if not isinstance(market, dict):
        return []

    labels = ODDSPAPI_OUTCOME_LABELS.get(str(market_id), {})
    outcomes: List[Dict[str, Any]] = []
    for outcome_id, outcome_data in (market.get("outcomes") or {}).items():
        if not isinstance(outcome_data, dict):
            continue
        player = (outcome_data.get("players") or {}).get("0") or {}
        if not player.get("active"):
            continue
        try:
            price = float(player.get("price"))
        except (TypeError, ValueError):
            continue
        if price <= 1.01:
            continue
        name = labels.get(str(outcome_id), str(outcome_id))
        outcomes.append({"name": name, "price": price})

    return outcomes


def _recommendations_from_oddspapi(
    bookmaker_odds: Dict[str, Any],
    league: str,
    sport: str,
    home: str,
    away: str,
) -> List[Dict[str, Any]]:
    pinnacle = bookmaker_odds.get(ODDSPAPI_BOOKMAKER) if isinstance(bookmaker_odds, dict) else None
    if not isinstance(pinnacle, dict):
        return []

    markets = pinnacle.get("markets") or {}
    if not isinstance(markets, dict):
        return []

    recommendations: List[Dict[str, Any]] = []
    support = 3.0

    for market_id in ODDSPAPI_PRIORITY_MARKETS:
        priced_outcomes = _oddspapi_market_outcomes(markets, market_id)
        if not priced_outcomes:
            continue

        probabilities = _compute_probabilities(priced_outcomes)
        for outcome in priced_outcomes[:3]:
            name = str(outcome.get("name") or "Исход")
            try:
                price = float(outcome.get("price"))
            except (TypeError, ValueError):
                continue
            probability = probabilities.get(name, round(min(0.99, 1.0 / price), 4))
            recommendations.append(
                {
                    "league": league,
                    "sport": sport,
                    "home": home,
                    "away": away,
                    "line": name,
                    "confidence": "high" if probability >= 0.45 else "med",
                    "probability": probability,
                    "coefficient": round(price, 2),
                    "bookmakers_support": support,
                }
            )

    return recommendations[:6]


def transform_oddspapi_event(
    fixture: Dict[str, Any],
    odds_row: Dict[str, Any],
    now_utc: datetime.datetime,
) -> Optional[Dict[str, Any]]:
    home = fixture.get("participant1Name")
    away = fixture.get("participant2Name")
    if not home or not away:
        return None

    sport = _oddspapi_normalize_sport(fixture.get("sportId") or odds_row.get("sportId"))
    league = (
        fixture.get("tournamentName")
        or fixture.get("categoryName")
        or fixture.get("sportName")
        or "Unknown League"
    )
    start_time = fixture.get("startTime") or odds_row.get("startTime")
    commence_dt = _parse_iso_datetime(start_time)
    status_id = fixture.get("statusId", odds_row.get("statusId", 0))
    is_live = status_id == 1 or bool(commence_dt and commence_dt <= now_utc)

    recommendations = _recommendations_from_oddspapi(
        odds_row.get("bookmakerOdds") or {},
        league,
        sport,
        home,
        away,
    )
    if not recommendations:
        return None

    fixture_id = str(fixture.get("fixtureId") or odds_row.get("fixtureId") or "")
    return {
        "id": f"op_{fixture_id}" if fixture_id else f"{sport}_{home}_{away}",
        "sport": sport,
        "league": league,
        "home": home,
        "away": away,
        "status": "LIVE" if is_live else "UPCOMING",
        "time": "LIVE" if is_live else _format_event_time(start_time),
        "score": "—",
        "is_live": is_live,
        "start_at": commence_dt.isoformat() if commence_dt else None,
        "recommendations": recommendations,
    }


def fetch_oddspapi_events_sync(limit: int = 80) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    if not resolve_oddspapi_key():
        return [], None

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    from_dt = (now_utc - datetime.timedelta(hours=6)).date().isoformat()
    to_dt = (now_utc + datetime.timedelta(hours=ODDSPAPI_FIXTURE_HORIZON_HOURS)).date().isoformat()

    fixture_by_id: Dict[str, Dict[str, Any]] = {}
    last_error: Optional[str] = None
    sport_ids = ODDSPAPI_SPORT_IDS or [10, 11, 15]

    for sport_id in sport_ids:
        payload, err = _oddspapi_get(
            "fixtures",
            {
                "sportId": sport_id,
                "from": from_dt,
                "to": to_dt,
                "hasOdds": "true",
                "bookmakers": ODDSPAPI_BOOKMAKER,
            },
        )
        time.sleep(ODDSPAPI_REQUEST_PAUSE_SECONDS)
        if err:
            last_error = err
        if payload == _RATE_LIMITED:
            break
        if not isinstance(payload, list):
            continue
        for row in payload:
            if not isinstance(row, dict):
                continue
            if row.get("statusId") not in (0, 1):
                continue
            commence_dt = _parse_iso_datetime(row.get("startTime"))
            if commence_dt and commence_dt < (now_utc - datetime.timedelta(hours=12)):
                continue
            fixture_id = str(row.get("fixtureId") or "")
            if fixture_id:
                fixture_by_id[fixture_id] = row

    if not fixture_by_id:
        return [], last_error or "oddspapi_no_fixtures"

    fixtures_sorted = sorted(
        fixture_by_id.values(),
        key=lambda row: (
            row.get("statusId") != 1,
            row.get("startTime") or "",
        ),
    )[: max(1, limit) * 3]

    tournament_ids: List[int] = []
    seen_tournaments = set()
    for row in fixtures_sorted:
        try:
            tournament_id = int(row.get("tournamentId"))
        except (TypeError, ValueError):
            continue
        if tournament_id in seen_tournaments:
            continue
        seen_tournaments.add(tournament_id)
        tournament_ids.append(tournament_id)
        if len(tournament_ids) >= ODDSPAPI_MAX_TOURNAMENTS_PER_REQUEST:
            break

    odds_by_fixture: Dict[str, Dict[str, Any]] = {}
    chunk = tournament_ids[:ODDSPAPI_MAX_TOURNAMENTS_PER_REQUEST]
    if chunk:
        payload, err = _oddspapi_get(
            "odds-by-tournaments",
            {
                "bookmaker": ODDSPAPI_BOOKMAKER,
                "tournamentIds": ",".join(str(tid) for tid in chunk),
                "oddsFormat": "decimal",
            },
        )
        time.sleep(ODDSPAPI_REQUEST_PAUSE_SECONDS)
        if err:
            last_error = err
        if isinstance(payload, list):
            for row in payload:
                if not isinstance(row, dict):
                    continue
                fixture_id = str(row.get("fixtureId") or "")
                if fixture_id:
                    odds_by_fixture[fixture_id] = row

    events: List[Dict[str, Any]] = []
    for fixture in fixtures_sorted:
        if len(events) >= max(1, limit):
            break
        fixture_id = str(fixture.get("fixtureId") or "")
        odds_row = odds_by_fixture.get(fixture_id)
        if not odds_row:
            continue
        transformed = transform_oddspapi_event(fixture, odds_row, now_utc)
        if transformed:
            events.append(transformed)

    if events:
        logger.info("OddsPapi: loaded %s storefront events", len(events))
        return events, None

    if not odds_by_fixture:
        return [], last_error or "oddspapi_no_odds"
    return [], last_error or "oddspapi_no_matching_odds"
