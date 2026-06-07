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


def _is_amvera_runtime() -> bool:
    return _is_truthy_env("AMVERA")


def _amvera_light_scrape() -> bool:
    """Low-CPU profile on Amvera unless full multi-sport scrape is explicitly requested."""
    return _is_amvera_runtime() and not _is_truthy_env("BOOKMAKER_SCRAPE_FULL_SPORTS")


def _bookmaker_scrape_enabled_from_env() -> bool:
    """Explicit BOOKMAKER_SCRAPE_ENABLED wins; on Amvera default to enabled."""
    explicit = os.getenv("BOOKMAKER_SCRAPE_ENABLED")
    if explicit is not None and explicit.strip() != "":
        return _is_truthy_env("BOOKMAKER_SCRAPE_ENABLED")
    return _is_truthy_env("AMVERA")


BOOKMAKER_SCRAPE_ENABLED = _bookmaker_scrape_enabled_from_env()
# Pari sport path slug -> internal sport key (verified via SSR HTML scrape)
PARI_SPORT_PAGES: Dict[str, str] = {
    "football": "football",
    "hockey": "hockey",
    "basketball": "basketball",
    "tennis": "tennis",
    "table-tennis": "table_tennis",
    "volleyball": "volleyball",
    "handball": "handball",
    "baseball": "baseball",
    "boxing": "boxing",
    "darts": "darts",
    "cricket": "cricket",
    "rugby": "rugby",
    "futsal": "futsal",
    "waterpolo": "water_polo",
    "badminton": "badminton",
}


_LEGACY_FOOTBALL_ONLY_URLS = {
    "https://pari.ru/live?dateInterval=5",
    "https://pari.ru/sports/football?dateInterval=5",
    "https://pari.ru/live/football?dateInterval=5",
}


def _light_bookmaker_scrape_urls() -> List[str]:
    return [
        "https://pari.ru/live?dateInterval=5",
        "https://pari.ru/sports/football?dateInterval=5",
        "https://pari.ru/sports/hockey?dateInterval=5",
        "https://pari.ru/sports/basketball?dateInterval=5",
    ]


def _default_bookmaker_scrape_urls() -> List[str]:
    if _amvera_light_scrape():
        return _light_bookmaker_scrape_urls()

    urls = ["https://pari.ru/live?dateInterval=5"]
    for slug in PARI_SPORT_PAGES:
        urls.append(f"https://pari.ru/sports/{slug}?dateInterval=5")
    return urls


def _normalize_scrape_url(url: str) -> str:
    return url.strip().rstrip("/")


def _resolve_bookmaker_scrape_urls() -> List[str]:
    """Use full multi-sport Pari pages unless caller overrides with a non-legacy list."""
    raw = (os.getenv("BOOKMAKER_SCRAPE_URLS") or "").strip()
    if not raw:
        return _default_bookmaker_scrape_urls()

    urls = [part.strip() for part in raw.split(",") if part.strip()]
    normalized = {_normalize_scrape_url(u) for u in urls}
    football_only = normalized.issubset(_LEGACY_FOOTBALL_ONLY_URLS) or (
        len(normalized) <= 3 and all("football" in u for u in normalized)
    )
    if football_only:
        if _amvera_light_scrape():
            logger.info(
                "Amvera light scrape: keeping %s legacy Pari URLs (set BOOKMAKER_SCRAPE_FULL_SPORTS=true for 16 pages)",
                len(urls),
            )
            return urls
        logger.warning(
            "BOOKMAKER_SCRAPE_URLS contains football-only legacy URLs; expanding to %s Pari sport pages",
            len(PARI_SPORT_PAGES) + 1,
        )
        return _default_bookmaker_scrape_urls()
    return urls


BOOKMAKER_SCRAPE_URLS = _resolve_bookmaker_scrape_urls()
BOOKMAKER_SCRAPE_URLS_EXPANDED_FROM_LEGACY = (os.getenv("BOOKMAKER_SCRAPE_URLS") or "").strip() != "" and set(
    _normalize_scrape_url(u) for u in BOOKMAKER_SCRAPE_URLS
) != {_normalize_scrape_url(u) for u in (os.getenv("BOOKMAKER_SCRAPE_URLS") or "").split(",") if u.strip()}
_AMVERA_LIGHT = _amvera_light_scrape()
BOOKMAKER_SCRAPE_INTERVAL_SECONDS = int(
    os.getenv("BOOKMAKER_SCRAPE_INTERVAL_SECONDS", "1800" if _AMVERA_LIGHT else "300")
)
BOOKMAKER_SCRAPE_CACHE_TTL_SECONDS = int(os.getenv("BOOKMAKER_SCRAPE_CACHE_TTL_SECONDS", "300"))
BOOKMAKER_SCRAPE_LIMIT = int(os.getenv("BOOKMAKER_SCRAPE_LIMIT", "80" if _AMVERA_LIGHT else "280"))
BOOKMAKER_SCRAPE_PER_URL_LIMIT = int(os.getenv("BOOKMAKER_SCRAPE_PER_URL_LIMIT", "8" if _AMVERA_LIGHT else "14"))
BOOKMAKER_SCRAPE_BATCH_SIZE = int(
    os.getenv(
        "BOOKMAKER_SCRAPE_BATCH_SIZE",
        "3" if _AMVERA_LIGHT else str(max(len(BOOKMAKER_SCRAPE_URLS), 1)),
    )
)
BOOKMAKER_SCRAPE_URL_PAUSE_SECONDS = float(
    os.getenv("BOOKMAKER_SCRAPE_URL_PAUSE_SECONDS", "1.0" if _AMVERA_LIGHT else "0.35")
)
BOOKMAKER_FETCH_TIMEOUT_SECONDS = int(os.getenv("BOOKMAKER_FETCH_TIMEOUT_SECONDS", "12" if _AMVERA_LIGHT else "18"))
BOOKMAKER_FETCH_MAX_BYTES = int(os.getenv("BOOKMAKER_FETCH_MAX_BYTES", "1000000" if _AMVERA_LIGHT else "2500000"))
BOOKMAKER_SCRAPE_REQUEST_PATH_SYNC = _is_truthy_env("BOOKMAKER_SCRAPE_REQUEST_PATH_SYNC")
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

_PARI_FACTOR_VALUE_RE = re.compile(
    r'value--[^"]*value--[^"]*">([0-9]+\.[0-9]{2})</',
    re.IGNORECASE,
)
_PARI_PARAM_RE = re.compile(
    r"factor-value_param[^>]*>.*?<div>(-?[0-9]+\.?[0-9]*)</div>",
    re.IGNORECASE | re.DOTALL,
)
_PARI_SUB_EVENT_RE = re.compile(
    r'sport-sub-event-name[^"]*"[^>]*>([^<]+)<',
    re.IGNORECASE,
)
BOOKMAKER_MAX_RECOMMENDATIONS = int(os.getenv("BOOKMAKER_MAX_RECOMMENDATIONS", "20" if _AMVERA_LIGHT else "40"))

_MAIN_MARKET_COLUMNS = ["1", "Х", "2", "ФОРА 1", "ФОРА 2", "Тотал", "Б", "М"]

_MAIN_SCOPE = "Матч"


def _score_unit(sport: str) -> str:
    if sport == "hockey":
        return "шайбы"
    if sport == "basketball":
        return "очки"
    if sport in ("tennis", "table_tennis", "volleyball", "badminton"):
        return "очки/геймы"
    return "голы"


def _unit_dative(unit: str) -> str:
    return {
        "голы": "голам",
        "шайбы": "шайбам",
        "очки": "очкам",
        "очки/геймы": "очкам/геймам",
    }.get(unit, unit)


def _sub_market_meta(sub_name: str) -> Tuple[str, str, float]:
    """Return display scope, line_detail hint, and preferred total line for sub-markets."""
    name = sub_name.strip()
    low = name.lower()
    if "углов" in low:
        return name, "Считаются только угловые удары (не голы в ворота).", 9.5
    if "жёлт" in low or "желт" in low or "жк" in low or "карт" in low:
        return name, "Считаются только жёлтые карточки (не голы и не угловые).", 4.5
    if "фол" in low:
        return name, "Считаются только фолы (отдельный рынок от голов).", 22.5
    if "офсайд" in low:
        return name, "Считаются только офсайды.", 3.5
    if "удар" in low and "створ" in low:
        return name, "Считаются только удары в створ (не голы 1X2).", 8.5
    if "удален" in low:
        return name, "Считаются удаления игроков.", 0.5
    return name, f"Отдельный рынок «{name}», не основной счёт матча.", 2.5


def _group_suffix(group_index: int) -> str:
    if group_index <= 0:
        return ""
    return f" (альтернативная линия {group_index + 1})"


def _handicap_labels(
    team: str,
    handicap: Optional[float],
    unit: str,
    book_side: str,
    group_suffix: str,
) -> Tuple[str, str]:
    if handicap is None:
        line = f"{_MAIN_SCOPE} · Фора {book_side}: {team}{group_suffix}"
        detail = (
            f"Фора {book_side} = ставка на {team}. Рынок по {_unit_dative(unit)}, основное время (не угловые/ЖК)."
        )
        return line, detail
    line = f"{_MAIN_SCOPE} · Фора по {_unit_dative(unit)}: {team} {handicap:+.1f}{group_suffix}"
    detail = (
        f"Ставка на {team} с форой {handicap:+.1f}: итог по {_unit_dative(unit)} с учётом форы, основное время."
    )
    return line, detail


def _outcome_label(
    column: str,
    *,
    home: str,
    away: str,
    unit: str,
    group_suffix: str,
) -> Tuple[str, str]:
    if column == "1":
        return (
            f"{_MAIN_SCOPE} · Победа {home} ({unit}, основное время){group_suffix}",
            f"Исход 1X2: победа {home} по {_unit_dative(unit)} в основное время.",
        )
    if column in {"Х", "X"}:
        return (
            f"{_MAIN_SCOPE} · Ничья ({unit}, основное время){group_suffix}",
            f"Исход 1X2: ничья по {_unit_dative(unit)} в основное время.",
        )
    if column == "2":
        return (
            f"{_MAIN_SCOPE} · Победа {away} ({unit}, основное время){group_suffix}",
            f"Исход 1X2: победа {away} по {_unit_dative(unit)} в основное время.",
        )
    return "", ""


def _total_labels(
    direction: str,
    total_line: float,
    unit: str,
    group_suffix: str,
) -> Tuple[str, str]:
    if direction == "over":
        line = f"{_MAIN_SCOPE} · Тотал {_unit_dative(unit)} больше {total_line}{group_suffix}"
        detail = f"Сумма {_unit_dative(unit)} обеих команд больше {total_line}, основное время."
    else:
        line = f"{_MAIN_SCOPE} · Тотал {_unit_dative(unit)} меньше {total_line}{group_suffix}"
        detail = f"Сумма {_unit_dative(unit)} обеих команд меньше {total_line}, основное время."
    return line, detail


def _sub_outcome_label(
    column: str,
    *,
    scope: str,
    home: str,
    away: str,
    unit_hint: str,
) -> Tuple[str, str]:
    if column == "1":
        return f"{scope} · {home} (исход 1)", f"{unit_hint} Победа {home} в этом рынке."
    if column in {"Х", "X"}:
        return f"{scope} · Ничья", f"{unit_hint} Равный исход в этом рынке."
    if column == "2":
        return f"{scope} · {away} (исход 2)", f"{unit_hint} Победа {away} в этом рынке."
    return "", ""


def _slice_event_chunk(html: str, start: int) -> str:
    next_match = _PARI_TEAM_RE.search(html, start + 80)
    end = next_match.start() if next_match else start + 28000
    end = min(end, start + 28000)
    return html[start:end]


def _pick_total_line(params: List[float], sport: str = "football") -> float:
    if sport == "hockey":
        preferred = 5.5
    elif sport == "basketball":
        preferred = 220.5
    elif sport in ("tennis", "table_tennis", "volleyball", "badminton"):
        preferred = 21.5
    else:
        preferred = 2.5
    candidates = [value for value in params if 1.0 <= value <= 6.5]
    if not candidates:
        candidates = [value for value in params if 0.5 <= value <= 8.5]
    if not candidates:
        return preferred
    return min(candidates, key=lambda value: abs(value - preferred))


def _pick_handicap_lines(params: List[float]) -> Tuple[Optional[float], Optional[float]]:
    handicaps = [value for value in params if -5.0 <= value <= 5.0 and value != 0]
    if not handicaps:
        return None, None
    if len(handicaps) == 1:
        return handicaps[0], None
    return handicaps[0], handicaps[1]


def _append_rec(
    recommendations: List[Dict[str, Any]],
    line: str,
    coefficient: float,
    now_utc: datetime.datetime,
    *,
    probability: Optional[float] = None,
    confidence: Optional[str] = None,
    market_scope: Optional[str] = None,
    line_detail: Optional[str] = None,
) -> None:
    if coefficient < 1.01 or coefficient > 100:
        return
    if probability is None:
        probability = min(0.97, max(0.05, (1.0 / coefficient) * 0.94))
    else:
        probability = min(0.97, max(0.05, probability))
    entry: Dict[str, Any] = {
        "line": line,
        "coefficient": round(coefficient, 2),
        "probability": round(probability, 4),
        "confidence": confidence or ("high" if probability >= 0.68 else "med"),
        "bookmakers_support": 3.0,
        "odds_updated_at": now_utc.isoformat(),
    }
    if market_scope:
        entry["market_scope"] = market_scope
    if line_detail:
        entry["line_detail"] = line_detail
    recommendations.append(entry)


def _double_chance_odds(c1: float, cx: float, c2: float, mode: str) -> Optional[float]:
    inv = {"1": 1.0 / c1, "X": 1.0 / cx, "2": 1.0 / c2}
    if mode == "1X":
        combined = inv["1"] + inv["X"]
    elif mode == "X2":
        combined = inv["X"] + inv["2"]
    elif mode == "12":
        combined = inv["1"] + inv["2"]
    else:
        return None
    if combined <= 0:
        return None
    return min(50.0, (1.0 / combined) * 0.97)


def _context_sub_name(chunk: str, position: int) -> str:
    best = ""
    for match in _PARI_SUB_EVENT_RE.finditer(chunk):
        if match.start() >= position:
            break
        name = unescape(match.group(1)).strip()
        if not name or name.lower() == "что раньше":
            continue
        best = name
    return best


def _append_main_market_group(
    recommendations: List[Dict[str, Any]],
    *,
    home: str,
    away: str,
    group_values: List[float],
    params: List[float],
    sport: str,
    now_utc: datetime.datetime,
    group_index: int,
) -> None:
    if len(group_values) < 3:
        return

    handicap1, handicap2 = _pick_handicap_lines(params)
    total_line = _pick_total_line(params, sport)
    unit = _score_unit(sport)
    group_suffix = _group_suffix(group_index)

    outcome_probs: Dict[str, float] = {}
    inv_sum = sum(1.0 / coef for coef in group_values[:3])
    if inv_sum > 0:
        outcome_probs = {
            "1": (1.0 / group_values[0]) / inv_sum,
            "Х": (1.0 / group_values[1]) / inv_sum,
            "2": (1.0 / group_values[2]) / inv_sum,
        }

    for idx, column in enumerate(_MAIN_MARKET_COLUMNS):
        if column == "Тотал":
            continue
        if idx >= len(group_values):
            break
        line = ""
        detail = ""
        if column in {"1", "Х", "X", "2"}:
            line, detail = _outcome_label(
                column,
                home=home,
                away=away,
                unit=unit,
                group_suffix=group_suffix,
            )
        elif column == "ФОРА 1":
            line, detail = _handicap_labels(home, handicap1, unit, "1", group_suffix)
        elif column == "ФОРА 2":
            line, detail = _handicap_labels(away, handicap2, unit, "2", group_suffix)
        elif column == "Б":
            line, detail = _total_labels("over", total_line, unit, group_suffix)
        elif column == "М":
            line, detail = _total_labels("under", total_line, unit, group_suffix)
        if not line:
            continue
        _append_rec(
            recommendations,
            line,
            group_values[idx],
            now_utc,
            probability=outcome_probs.get(column),
            market_scope=_MAIN_SCOPE,
            line_detail=detail,
        )

    if group_index == 0 and len(group_values) >= 3:
        c1, cx, c2 = group_values[0], group_values[1], group_values[2]
        for mode, label, detail in (
            (
                "1X",
                f"{_MAIN_SCOPE} · Двойной шанс 1X: {home} или ничья",
                f"По {_unit_dative(unit)}: не проигрыш {home} (победа или ничья), основное время.",
            ),
            (
                "X2",
                f"{_MAIN_SCOPE} · Двойной шанс X2: ничья или {away}",
                f"По {_unit_dative(unit)}: не проигрыш {away} (ничья или победа), основное время.",
            ),
            (
                "12",
                f"{_MAIN_SCOPE} · Двойной шанс 12: {home} или {away}",
                f"По {_unit_dative(unit)}: победа одной из сторон без ничьей, основное время.",
            ),
        ):
            combo = _double_chance_odds(c1, cx, c2, mode)
            if combo:
                _append_rec(
                    recommendations,
                    label,
                    combo,
                    now_utc,
                    market_scope=_MAIN_SCOPE,
                    line_detail=detail,
                )

def _recommendations_from_pari_chunk(
    home: str,
    away: str,
    chunk: str,
    sport: str,
    now_utc: datetime.datetime,
) -> List[Dict[str, Any]]:
    recommendations: List[Dict[str, Any]] = []
    params: List[float] = []
    for raw in _PARI_PARAM_RE.findall(chunk):
        try:
            params.append(float(raw))
        except ValueError:
            continue

    value_hits = [(m.start(), float(m.group(1))) for m in _PARI_FACTOR_VALUE_RE.finditer(chunk)]
    if len(value_hits) < 3:
        return []

    values = [coef for _, coef in value_hits]
    for group_index in range(0, len(values), 8):
        group_values = values[group_index : group_index + 8]
        if len(group_values) < 3:
            continue
        pos = value_hits[group_index][0]
        sub_name = _context_sub_name(chunk, pos)
        if sub_name:
            scope, unit_hint, preferred_total = _sub_market_meta(sub_name)
            sub_candidates = [value for value in params if 0.5 <= value <= 25.5]
            if sub_candidates:
                sub_total = min(sub_candidates, key=lambda value: abs(value - preferred_total))
            else:
                sub_total = preferred_total
            for idx, column in enumerate(("1", "X", "2")[: len(group_values)]):
                line, detail = _sub_outcome_label(
                    column,
                    scope=scope,
                    home=home,
                    away=away,
                    unit_hint=unit_hint,
                )
                if line:
                    _append_rec(
                        recommendations,
                        line,
                        group_values[idx],
                        now_utc,
                        market_scope=scope,
                        line_detail=detail,
                    )
            if len(group_values) >= 5:
                _append_rec(
                    recommendations,
                    f"{scope} · Тотал больше {sub_total}",
                    group_values[3],
                    now_utc,
                    market_scope=scope,
                    line_detail=f"{unit_hint} Сумма показателя больше {sub_total}.",
                )
                _append_rec(
                    recommendations,
                    f"{scope} · Тотал меньше {sub_total}",
                    group_values[4],
                    now_utc,
                    market_scope=scope,
                    line_detail=f"{unit_hint} Сумма показателя меньше {sub_total}.",
                )
            for extra_idx, coef in enumerate(group_values[5:8], start=6):
                _append_rec(
                    recommendations,
                    f"{scope} · Доп. коэффициент (поз. {extra_idx})",
                    coef,
                    now_utc,
                    market_scope=scope,
                    line_detail=unit_hint,
                )
            continue

        _append_main_market_group(
            recommendations,
            home=home,
            away=away,
            group_values=group_values,
            params=params,
            sport=sport,
            now_utc=now_utc,
            group_index=group_index // 8,
        )

    if sport == "tennis":
        recommendations = [
            rec
            for rec in recommendations
            if "Ничья" not in rec["line"] and "X2" not in rec["line"] and "1X" not in rec["line"]
        ]

    deduped: List[Dict[str, Any]] = []
    seen_lines = set()
    for rec in sorted(recommendations, key=lambda item: (-item["probability"], -item["coefficient"])):
        key = rec["line"]
        if key in seen_lines:
            continue
        seen_lines.add(key)
        deduped.append(rec)
        if len(deduped) >= BOOKMAKER_MAX_RECOMMENDATIONS:
            break
    return deduped


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
        "настольный теннис": "table_tennis",
        "table tennis": "table_tennis",
        "table-tennis": "table_tennis",
        "волейбол": "volleyball",
        "volleyball": "volleyball",
        "гандбол": "handball",
        "handball": "handball",
        "бейсбол": "baseball",
        "baseball": "baseball",
        "бокс": "boxing",
        "boxing": "boxing",
        "киберспорт": "esports",
        "esports": "esports",
        "cs2": "esports",
        "дартс": "darts",
        "darts": "darts",
        "крикет": "cricket",
        "cricket": "cricket",
        "регби": "rugby",
        "rugby": "rugby",
        "футзал": "futsal",
        "futsal": "futsal",
        "водное поло": "water_polo",
        "water polo": "water_polo",
        "waterpolo": "water_polo",
        "бадминтон": "badminton",
        "badminton": "badminton",
    }
    if value in mapping:
        return mapping[value]
    url = source_url.lower()
    for slug, sport_key in PARI_SPORT_PAGES.items():
        if f"/{slug}" in url:
            return sport_key
    if "/esport" in url:
        return "esports"
    if "/live" in url and not value:
        return "football"
    return mapping.get(value, value.replace(" ", "_") or "other")



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
    for slug, sport_key in PARI_SPORT_PAGES.items():
        if f"/{slug}" in url:
            return sport_key
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
        chunk = _slice_event_chunk(html, match.start())

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

        recommendations = _recommendations_from_pari_chunk(home, away, chunk, sport, now_utc)
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
        with urllib_request.urlopen(req, timeout=BOOKMAKER_FETCH_TIMEOUT_SECONDS) as response:
            body = response.read(BOOKMAKER_FETCH_MAX_BYTES + 1)
            if len(body) > BOOKMAKER_FETCH_MAX_BYTES:
                body = body[:BOOKMAKER_FETCH_MAX_BYTES]
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

    for index, url in enumerate(targets):
        if index > 0 and BOOKMAKER_SCRAPE_URL_PAUSE_SECONDS > 0:
            time.sleep(BOOKMAKER_SCRAPE_URL_PAUSE_SECONDS)
        html, err = _fetch_url(url)
        if err:
            last_error = f"bookmaker_{err}"
            logger.warning("Bookmaker scrape failed for %s: %s", url, err)
            continue
        if not html:
            continue
        per_url_cap = min(BOOKMAKER_SCRAPE_PER_URL_LIMIT, max(6, limit // max(len(targets), 1)))
        added_here = 0
        for event in _extract_events_from_html(html, url):
            if event["id"] in seen_ids:
                continue
            seen_ids.add(event["id"])
            merged.append(event)
            added_here += 1
            if added_here >= per_url_cap or len(merged) >= limit:
                break
        if len(merged) >= limit:
            break

    if os.getenv("WINLINE_SCRAPE_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}:
        try:
            from winline_scrape_source import scrape_winline_events_sync

            winline_events, winline_err = scrape_winline_events_sync()
            if winline_err:
                last_error = last_error or winline_err
            for event in winline_events:
                if event.get("id") in seen_ids:
                    continue
                seen_ids.add(event["id"])
                merged.append(event)
        except Exception as exc:
            logger.warning("Winline scrape hook failed: %s", exc)

    if os.getenv("MELBET_SCRAPE_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}:
        try:
            from melbet_scrape_source import scrape_melbet_events_sync

            melbet_events, melbet_err = scrape_melbet_events_sync(limit=max(20, limit - len(merged)))
            if melbet_err:
                last_error = last_error or melbet_err
            for event in melbet_events:
                eid = event.get("id")
                if eid in seen_ids:
                    continue
                seen_ids.add(eid)
                merged.append(event)
        except Exception as exc:
            logger.warning("Melbet scrape hook failed: %s", exc)

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
_scrape_in_progress = False
_scrape_batch_rotation_index = 0
_scrape_refresh_requested = threading.Event()
_scrape_state_lock = threading.Lock()


def _merge_bookmaker_events(
    existing: List[Dict[str, Any]],
    incoming: List[Dict[str, Any]],
    limit: int,
) -> List[Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    for event in existing:
        event_id = str(event.get("id") or "")
        if event_id:
            merged[event_id] = event
    for event in incoming:
        event_id = str(event.get("id") or "")
        if event_id:
            merged[event_id] = event
    return list(merged.values())[: max(1, limit)]


def _urls_for_scrape_cycle() -> List[str]:
    global _scrape_batch_rotation_index
    all_urls = list(BOOKMAKER_SCRAPE_URLS)
    if not all_urls:
        return []

    batch_size = max(1, min(BOOKMAKER_SCRAPE_BATCH_SIZE, len(all_urls)))
    if batch_size >= len(all_urls):
        return all_urls

    start = _scrape_batch_rotation_index % len(all_urls)
    selected = [all_urls[(start + index) % len(all_urls)] for index in range(batch_size)]
    _scrape_batch_rotation_index = (start + batch_size) % len(all_urls)
    return selected


def _store_bookmaker_scrape_result(
    events: List[Dict[str, Any]],
    err: Optional[str],
    now_ts: float,
    scraped_urls: Optional[List[str]] = None,
) -> None:
    with _cache_lock:
        cached = list(_cache.get("events") or [])
        if events:
            if BOOKMAKER_SCRAPE_BATCH_SIZE < len(BOOKMAKER_SCRAPE_URLS):
                events = _merge_bookmaker_events(cached, events, BOOKMAKER_SCRAPE_LIMIT)
            _cache["events"] = events
            _cache["ts"] = now_ts
            _cache["source"] = "bookmaker_scrape"
            _cache["last_error"] = None
            _cache["last_urls"] = list(scraped_urls or BOOKMAKER_SCRAPE_URLS)
            return
        if cached:
            _cache["last_error"] = err
            return
        _cache["events"] = []
        _cache["ts"] = now_ts
        _cache["last_error"] = err


def _run_bookmaker_scrape_once() -> None:
    global _scrape_in_progress
    with _scrape_state_lock:
        if _scrape_in_progress:
            return
        _scrape_in_progress = True

    try:
        targets = _urls_for_scrape_cycle()
        events, err = scrape_bookmaker_urls_sync(urls=targets)
        _store_bookmaker_scrape_result(events, err, time.time(), targets)
    except Exception as exc:
        logger.warning("Bookmaker background scrape error: %s", exc)
        _store_bookmaker_scrape_result([], str(exc), time.time(), [])
    finally:
        with _scrape_state_lock:
            _scrape_in_progress = False


def request_bookmaker_scrape_refresh() -> None:
    _scrape_refresh_requested.set()


def _wait_for_bookmaker_scrape(timeout_seconds: float) -> None:
    deadline = time.time() + max(0.0, timeout_seconds)
    while time.time() < deadline:
        with _scrape_state_lock:
            if not _scrape_in_progress:
                return
        time.sleep(0.2)


def _ensure_background_scrape_started() -> None:
    global _scrape_thread_started
    if _scrape_thread_started or not BOOKMAKER_SCRAPE_ENABLED:
        return
    _scrape_thread_started = True

    def _loop() -> None:
        startup_delay = int(
            os.getenv(
                "BOOKMAKER_SCRAPE_STARTUP_DELAY_SECONDS",
                "90" if _is_amvera_runtime() else "5",
            )
        )
        if startup_delay > 0:
            logger.info("Bookmaker scrape first run delayed by %ss (let HTTP workers pass health checks)", startup_delay)
            time.sleep(startup_delay)

        while BOOKMAKER_SCRAPE_ENABLED:
            _run_bookmaker_scrape_once()
            wait_seconds = max(60, BOOKMAKER_SCRAPE_INTERVAL_SECONDS)
            if _scrape_refresh_requested.wait(timeout=wait_seconds):
                _scrape_refresh_requested.clear()

    threading.Thread(target=_loop, name="bookmaker-scrape", daemon=True).start()
    logger.info(
        "Bookmaker background scrape started (interval=%ss, urls=%s, batch=%s, light_mode=%s)",
        BOOKMAKER_SCRAPE_INTERVAL_SECONDS,
        BOOKMAKER_SCRAPE_URLS,
        BOOKMAKER_SCRAPE_BATCH_SIZE,
        _AMVERA_LIGHT,
    )


def get_cached_bookmaker_events(force_refresh: bool = False) -> List[Dict[str, Any]]:
    """Return cached bookmaker events without blocking HTTP workers on scrape."""
    _ensure_background_scrape_started()
    if force_refresh:
        request_bookmaker_scrape_refresh()

    with _cache_lock:
        cached = list(_cache.get("events") or [])

    if BOOKMAKER_SCRAPE_REQUEST_PATH_SYNC and (force_refresh or not cached):
        with _scrape_state_lock:
            scrape_active = _scrape_in_progress
        if scrape_active:
            _wait_for_bookmaker_scrape(timeout_seconds=120.0)
        else:
            _run_bookmaker_scrape_once()
        with _cache_lock:
            cached = list(_cache.get("events") or [])

    return cached


def get_status_snapshot() -> Dict[str, Any]:
    with _cache_lock:
        return {
            "enabled": BOOKMAKER_SCRAPE_ENABLED,
            "urls": list(BOOKMAKER_SCRAPE_URLS),
            "interval_seconds": BOOKMAKER_SCRAPE_INTERVAL_SECONDS,
            "cache_ttl_seconds": BOOKMAKER_SCRAPE_CACHE_TTL_SECONDS,
            "cached_events": len(_cache.get("events") or []),
            "scrape_in_progress": _scrape_in_progress,
            "source": _cache.get("source"),
            "last_error": _cache.get("last_error"),
            "cache_age_seconds": max(0, int(time.time() - float(_cache.get("ts") or 0.0))),
            "ingest_configured": bool(BOOKMAKER_INGEST_SECRET),
            "max_recommendations_per_event": BOOKMAKER_MAX_RECOMMENDATIONS,
            "sport_pages": list(PARI_SPORT_PAGES.keys()),
            "scrape_per_url_limit": BOOKMAKER_SCRAPE_PER_URL_LIMIT,
            "urls_expanded_from_legacy": BOOKMAKER_SCRAPE_URLS_EXPANDED_FROM_LEGACY,
            "batch_size": BOOKMAKER_SCRAPE_BATCH_SIZE,
            "light_mode": _AMVERA_LIGHT,
            "last_scraped_urls": list(_cache.get("last_urls") or []),
            "winline": _winline_status_snapshot(),
            "melbet": _melbet_status_snapshot(),
        }


def _winline_status_snapshot() -> Dict[str, Any]:
    try:
        from winline_scrape_source import get_status_snapshot as winline_status

        return winline_status()
    except Exception as exc:
        return {"enabled": False, "error": str(exc)}


def _melbet_status_snapshot() -> Dict[str, Any]:
    try:
        from melbet_scrape_source import get_status_snapshot as melbet_status

        return melbet_status()
    except Exception as exc:
        return {"enabled": False, "error": str(exc)}

