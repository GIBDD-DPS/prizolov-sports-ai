# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v12.0 (LIVE SPORTS)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

import sys
import os
import logging
import pathlib
import datetime
import asyncio
import copy
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("PrizolovSportsAI.Main")

# Гарантируем, что текущая папка (app/) находится в системных путях
current_dir = pathlib.Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Инициализация приложения FastAPI
app = FastAPI(title="Prizolov Sports AI", version="12.0")

# Глобальный CORS для связи с prizolov.ru
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# LIVE СОБЫТИЯ ПО ВИДАМ СПОРТА
# ============================================

LIVE_EVENTS = [
    # ===== ФУТБОЛ =====
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
        ]
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
        ]
    },
    {
        "id": "f3",
        "sport": "football",
        "league": "Premier League",
        "home": "Manchester City",
        "away": "Liverpool",
        "status": "LIVE",
        "time": "72'",
        "score": "2-2",
        "recommendations": [
            {"line": "Тотал больше 3.5", "coefficient": 2.15, "probability": 0.68, "confidence": "high"},
            {"line": "Ничья", "coefficient": 3.50, "probability": 0.35, "confidence": "med"},
            {"line": "Тотал больше 2.5", "coefficient": 1.45, "probability": 0.91, "confidence": "high"},
        ]
    },
    {
        "id": "f4",
        "sport": "football",
        "league": "Serie A",
        "home": "AC Milan",
        "away": "Inter",
        "status": "LIVE",
        "time": "38'",
        "score": "1-0",
        "recommendations": [
            {"line": "Тотал больше 2.5", "coefficient": 1.78, "probability": 0.75, "confidence": "high"},
            {"line": "Обе забьют - ДА", "coefficient": 1.95, "probability": 0.72, "confidence": "med"},
        ]
    },
    
    # ===== ХОККЕЙ =====
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
            {"line": "Победа 1 (основное время)", "coefficient": 1.88, "probability": 0.68, "confidence": "med"},
        ]
    },
    {
        "id": "h2",
        "sport": "hockey",
        "league": "NHL",
        "home": "New York Rangers",
        "away": "Boston Bruins",
        "status": "LIVE",
        "time": "1:45",
        "score": "2-1",
        "recommendations": [
            {"line": "Тотал больше 5.5", "coefficient": 1.95, "probability": 0.76, "confidence": "high"},
            {"line": "Обе забьют - ДА", "coefficient": 1.58, "probability": 0.88, "confidence": "high"},
        ]
    },
    {
        "id": "h3",
        "sport": "hockey",
        "league": "КХЛ",
        "home": "ЦСКА",
        "away": "СКА",
        "status": "LIVE",
        "time": "3:20",
        "score": "4-3",
        "recommendations": [
            {"line": "Тотал больше 6.5", "coefficient": 2.05, "probability": 0.72, "confidence": "high"},
            {"line": "Обе забьют - ДА", "coefficient": 1.52, "probability": 0.90, "confidence": "high"},
        ]
    },
    
    # ===== БАСКЕТБОЛ =====
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
            {"line": "Тотал больше 215.5", "coefficient": 2.25, "probability": 0.65, "confidence": "med"},
        ]
    },
    {
        "id": "b2",
        "sport": "basketball",
        "league": "EuroLeague",
        "home": "Real Madrid",
        "away": "FC Barcelona",
        "status": "LIVE",
        "time": "3 четверть",
        "score": "52-49",
        "recommendations": [
            {"line": "Тотал больше 151.5", "coefficient": 1.92, "probability": 0.74, "confidence": "high"},
            {"line": "Обе забьют более 73 очков", "coefficient": 1.78, "probability": 0.80, "confidence": "high"},
        ]
    },
    {
        "id": "b3",
        "sport": "basketball",
        "league": "NBL Australia",
        "home": "Sydney Kings",
        "away": "Melbourne United",
        "status": "LIVE",
        "time": "1 четверть",
        "score": "28-25",
        "recommendations": [
            {"line": "Тотал больше 170.5", "coefficient": 1.85, "probability": 0.79, "confidence": "high"},
            {"line": "Победа 1", "coefficient": 1.72, "probability": 0.75, "confidence": "med"},
        ]
    },
    
    # ===== ТЕННИС =====
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
        ]
    },
    {
        "id": "t2",
        "sport": "tennis",
        "league": "WTA",
        "home": "Iga Świątek",
        "away": "Elena Rybakina",
        "status": "LIVE",
        "time": "1 сет 5:3",
        "score": "0-0",
        "recommendations": [
            {"line": "Тотал геймов больше 20.5", "coefficient": 1.95, "probability": 0.71, "confidence": "high"},
            {"line": "Будет тайбрейк", "coefficient": 2.20, "probability": 0.58, "confidence": "med"},
        ]
    },
    
    # ===== ВОЛЕЙБОЛ =====
    {
        "id": "v1",
        "sport": "volleyball",
        "league": "European League",
        "home": "France",
        "away": "Poland",
        "status": "LIVE",
        "time": "2 сет 18:16",
        "score": "1-0",
        "recommendations": [
            {"line": "Тотал сетов больше 4.5", "coefficient": 1.82, "probability": 0.78, "confidence": "high"},
            {"line": "Победа 1", "coefficient": 1.65, "probability": 0.73, "confidence": "med"},
        ]
    },
    
    # ===== ГАНДБОЛ =====
    {
        "id": "g1",
        "sport": "handball",
        "league": "Champions League",
        "home": "Paris Saint-Germain",
        "away": "Barcelona",
        "status": "LIVE",
        "time": "30 мин",
        "score": "16-14",
        "recommendations": [
            {"line": "Тотал больше 54.5", "coefficient": 1.90, "probability": 0.75, "confidence": "high"},
            {"line": "Обе забьют более 27 голов", "coefficient": 1.72, "probability": 0.81, "confidence": "high"},
        ]
    },
    
    # ===== КИБЕР-СПОРТ =====
    {
        "id": "e1",
        "sport": "esports",
        "league": "CS:GO Pro League",
        "home": "FaZe Clan",
        "away": "NAVI",
        "status": "LIVE",
        "time": "Map 2 - 8:7",
        "score": "1-0",
        "recommendations": [
            {"line": "Победа 1", "coefficient": 1.78, "probability": 0.70, "confidence": "med"},
            {"line": "Матч пойдет на 3-ю карту", "coefficient": 2.10, "probability": 0.65, "confidence": "high"},
        ]
    },
]

UPCOMING_EVENT_TEMPLATES = [
    {
        "id": "u1",
        "sport": "football",
        "league": "Bundesliga",
        "home": "Bayern Munich",
        "away": "Borussia Dortmund",
        "starts_in_hours": 1.0,
        "recommendations": [
            {"line": "Тотал больше 2.5", "coefficient": 1.76, "probability": 0.74, "confidence": "high"},
            {"line": "Обе забьют - ДА", "coefficient": 1.70, "probability": 0.77, "confidence": "high"},
        ],
    },
    {
        "id": "u2",
        "sport": "hockey",
        "league": "NHL",
        "home": "Edmonton Oilers",
        "away": "Colorado Avalanche",
        "starts_in_hours": 2.5,
        "recommendations": [
            {"line": "Тотал больше 5.5", "coefficient": 1.90, "probability": 0.72, "confidence": "high"},
            {"line": "Обе забьют - ДА", "coefficient": 1.62, "probability": 0.82, "confidence": "high"},
        ],
    },
    {
        "id": "u3",
        "sport": "basketball",
        "league": "NBA",
        "home": "Phoenix Suns",
        "away": "Denver Nuggets",
        "starts_in_hours": 3.0,
        "recommendations": [
            {"line": "Тотал больше 221.5", "coefficient": 1.98, "probability": 0.69, "confidence": "high"},
            {"line": "Фора 1 (+4.5)", "coefficient": 1.72, "probability": 0.73, "confidence": "med"},
        ],
    },
    {
        "id": "u4",
        "sport": "tennis",
        "league": "ATP",
        "home": "Carlos Alcaraz",
        "away": "Daniil Medvedev",
        "starts_in_hours": 4.0,
        "recommendations": [
            {"line": "Тотал геймов больше 22.5", "coefficient": 1.91, "probability": 0.70, "confidence": "high"},
            {"line": "Победа 1", "coefficient": 1.83, "probability": 0.67, "confidence": "med"},
        ],
    },
    {
        "id": "u5",
        "sport": "volleyball",
        "league": "FIVB Nations League",
        "home": "Brazil",
        "away": "Italy",
        "starts_in_hours": 5.5,
        "recommendations": [
            {"line": "Тотал сетов больше 3.5", "coefficient": 1.68, "probability": 0.79, "confidence": "high"},
            {"line": "Победа 2", "coefficient": 2.08, "probability": 0.61, "confidence": "med"},
        ],
    },
    {
        "id": "u6",
        "sport": "handball",
        "league": "EHF Champions League",
        "home": "Kiel",
        "away": "Veszprem",
        "starts_in_hours": 6.0,
        "recommendations": [
            {"line": "Тотал больше 56.5", "coefficient": 1.88, "probability": 0.72, "confidence": "high"},
            {"line": "Обе забьют более 27", "coefficient": 1.66, "probability": 0.78, "confidence": "high"},
        ],
    },
    {
        "id": "u7",
        "sport": "esports",
        "league": "CS2 Major",
        "home": "G2",
        "away": "Vitality",
        "starts_in_hours": 7.0,
        "recommendations": [
            {"line": "Матч пойдет на 3-ю карту", "coefficient": 2.04, "probability": 0.64, "confidence": "high"},
            {"line": "Победа 1", "coefficient": 1.84, "probability": 0.66, "confidence": "med"},
        ],
    },
    {
        "id": "u8",
        "sport": "mma",
        "league": "UFC Fight Night",
        "home": "Fighter A",
        "away": "Fighter B",
        "starts_in_hours": 8.5,
        "recommendations": [
            {"line": "Победа 1", "coefficient": 1.95, "probability": 0.65, "confidence": "med"},
            {"line": "Бой продлится 3 раунда", "coefficient": 1.74, "probability": 0.71, "confidence": "high"},
        ],
    },
    {
        "id": "u9",
        "sport": "baseball",
        "league": "MLB",
        "home": "Yankees",
        "away": "Dodgers",
        "starts_in_hours": 9.0,
        "recommendations": [
            {"line": "Тотал больше 8.5", "coefficient": 1.86, "probability": 0.70, "confidence": "high"},
            {"line": "Победа 2", "coefficient": 2.02, "probability": 0.62, "confidence": "med"},
        ],
    },
    {
        "id": "u10",
        "sport": "american_football",
        "league": "NFL",
        "home": "Chiefs",
        "away": "Bills",
        "starts_in_hours": 11.0,
        "recommendations": [
            {"line": "Тотал больше 48.5", "coefficient": 1.92, "probability": 0.69, "confidence": "high"},
            {"line": "Фора 1 (-2.5)", "coefficient": 1.78, "probability": 0.67, "confidence": "med"},
        ],
    },
    {
        "id": "u11",
        "sport": "rugby",
        "league": "Super Rugby",
        "home": "Crusaders",
        "away": "Blues",
        "starts_in_hours": 12.0,
        "recommendations": [
            {"line": "Тотал больше 43.5", "coefficient": 1.84, "probability": 0.72, "confidence": "high"},
            {"line": "Победа 1", "coefficient": 1.88, "probability": 0.66, "confidence": "med"},
        ],
    },
    {
        "id": "u12",
        "sport": "cricket",
        "league": "T20 League",
        "home": "Mumbai",
        "away": "Chennai",
        "starts_in_hours": 13.5,
        "recommendations": [
            {"line": "Тотал ранов больше 168.5", "coefficient": 1.80, "probability": 0.73, "confidence": "high"},
            {"line": "Победа 2", "coefficient": 2.15, "probability": 0.60, "confidence": "med"},
        ],
    },
    {
        "id": "u13",
        "sport": "futsal",
        "league": "UEFA Futsal Cup",
        "home": "Sporting",
        "away": "Benfica",
        "starts_in_hours": 15.0,
        "recommendations": [
            {"line": "Тотал больше 5.5", "coefficient": 1.86, "probability": 0.71, "confidence": "high"},
            {"line": "Обе забьют - ДА", "coefficient": 1.58, "probability": 0.83, "confidence": "high"},
        ],
    },
    {
        "id": "u14",
        "sport": "table_tennis",
        "league": "WTT",
        "home": "Fan Zhendong",
        "away": "Ma Long",
        "starts_in_hours": 18.0,
        "recommendations": [
            {"line": "Тотал сетов больше 4.5", "coefficient": 1.93, "probability": 0.67, "confidence": "high"},
            {"line": "Победа 1", "coefficient": 1.70, "probability": 0.74, "confidence": "med"},
        ],
    },
    {
        "id": "u15",
        "sport": "badminton",
        "league": "BWF World Tour",
        "home": "Axelsen",
        "away": "Kodai Naraoka",
        "starts_in_hours": 20.0,
        "recommendations": [
            {"line": "Тотал очков больше 74.5", "coefficient": 1.82, "probability": 0.70, "confidence": "high"},
            {"line": "Победа 1", "coefficient": 1.62, "probability": 0.78, "confidence": "high"},
        ],
    },
    {
        "id": "u16",
        "sport": "boxing",
        "league": "World Boxing Series",
        "home": "Boxer A",
        "away": "Boxer B",
        "starts_in_hours": 22.0,
        "recommendations": [
            {"line": "Победа 1", "coefficient": 1.88, "probability": 0.66, "confidence": "med"},
            {"line": "Бой продлится весь лимит", "coefficient": 1.73, "probability": 0.72, "confidence": "high"},
        ],
    },
]

DEFAULT_WINDOW_HOURS = int(os.getenv("DEFAULT_WINDOW_HOURS", "24"))
DEFAULT_MIN_PROBABILITY = float(os.getenv("DEFAULT_MIN_PROBABILITY", "0.6"))
DEFAULT_MIN_COEFFICIENT = float(os.getenv("DEFAULT_MIN_COEFFICIENT", "1.5"))


def _safe_bool(value, default=True):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _coerce_int(value, default, minimum=None, maximum=None):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    if minimum is not None:
        parsed = max(minimum, parsed)
    if maximum is not None:
        parsed = min(maximum, parsed)
    return parsed


def _coerce_float(value, default, minimum=None, maximum=None):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    if minimum is not None:
        parsed = max(minimum, parsed)
    if maximum is not None:
        parsed = min(maximum, parsed)
    return parsed


def _event_pass_probability(event):
    recs = event.get("recommendations", [])
    if not recs:
        return 0.0
    return max(r.get("probability", 0.0) for r in recs)


def _build_upcoming_event(template, now_utc):
    event = copy.deepcopy(template)
    starts_in_hours = _coerce_float(event.pop("starts_in_hours", 0), 0.0, minimum=0.0)
    kickoff = now_utc + datetime.timedelta(hours=starts_in_hours)
    event["status"] = "UPCOMING"
    event["time"] = kickoff.strftime("%d.%m %H:%M UTC")
    event["score"] = "—"
    event["start_at"] = kickoff.isoformat()
    event["is_live"] = False
    return event


def _build_live_event(event, now_utc):
    event_copy = copy.deepcopy(event)
    event_copy["start_at"] = now_utc.isoformat()
    event_copy["is_live"] = True
    return event_copy


def _collect_window_events(window_hours=DEFAULT_WINDOW_HOURS, include_live=True):
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    events = []

    if include_live:
        for event in LIVE_EVENTS:
            events.append(_build_live_event(event, now_utc))

    for template in UPCOMING_EVENT_TEMPLATES:
        event = _build_upcoming_event(template, now_utc)
        kickoff = datetime.datetime.fromisoformat(event["start_at"])
        if kickoff <= now_utc + datetime.timedelta(hours=window_hours):
            events.append(event)

    return events


def _filter_and_rank_events(
    events,
    min_probability=DEFAULT_MIN_PROBABILITY,
    min_coefficient=DEFAULT_MIN_COEFFICIENT,
    passable_only=True,
    sort_by="passability",
):
    prepared = []
    for event in events:
        recommendations = event.get("recommendations", [])
        passable_recommendations = [
            r
            for r in recommendations
            if _coerce_float(r.get("probability"), 0.0) > min_probability
            and _coerce_float(r.get("coefficient"), 0.0) >= min_coefficient
        ]

        event_copy = copy.deepcopy(event)
        event_copy["passable_recommendations_count"] = len(passable_recommendations)
        event_copy["top_probability"] = (
            max(r.get("probability", 0.0) for r in passable_recommendations)
            if passable_recommendations
            else 0.0
        )

        if passable_only:
            event_copy["recommendations"] = passable_recommendations
            if not passable_recommendations:
                continue
        else:
            event_copy["passable_recommendations"] = passable_recommendations

        prepared.append(event_copy)

    if sort_by == "time":
        prepared.sort(key=lambda e: e.get("start_at", ""))
    else:
        prepared.sort(
            key=lambda e: (
                -_coerce_float(e.get("top_probability"), 0.0),
                e.get("start_at", ""),
            )
        )
    return prepared


def _sports_line(events):
    sports_map = {}
    for event in events:
        sport = event.get("sport", "unknown")
        sports_map[sport] = sports_map.get(sport, 0) + 1
    return dict(sorted(sports_map.items(), key=lambda item: (-item[1], item[0])))


def _build_match_payload(event):
    recommendations = []
    for rec in event.get("recommendations", []):
        recommendations.append({
            "league": event["league"],
            "sport": event["sport"],
            "home": event["home"],
            "away": event["away"],
            "line": rec["line"],
            "confidence": rec["confidence"],
            "probability": rec["probability"],
            "coefficient": rec["coefficient"],
        })
    return {
        "match_info": {
            "league": event["league"],
            "home": event["home"],
            "away": event["away"],
            "status": f"{event['time']} ({event['score']})" if event.get("score") else event.get("time", "—"),
            "sport": event["sport"],
            "start_at": event.get("start_at"),
            "is_live": event.get("is_live", False),
        },
        "recommendations": recommendations,
    }


async def _read_json_payload(request: Request = None):
    if request is None:
        return {}
    try:
        payload = await request.json()
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _collect_events_for_response(
    window_hours=DEFAULT_WINDOW_HOURS,
    include_live=True,
    min_probability=DEFAULT_MIN_PROBABILITY,
    min_coefficient=DEFAULT_MIN_COEFFICIENT,
    passable_only=True,
    sort_by="passability",
):
    pool = _collect_window_events(window_hours=window_hours, include_live=include_live)
    return _filter_and_rank_events(
        pool,
        min_probability=min_probability,
        min_coefficient=min_coefficient,
        passable_only=passable_only,
        sort_by=sort_by,
    )


def get_all_live_matches():
    """Совместимость: вернуть актуальный пул событий."""
    return _collect_events_for_response()


def get_matches_by_sport(sport):
    """Получить события по виду спорта с учетом фильтров по проходности."""
    sport_key = str(sport or "").lower().strip()
    return [e for e in _collect_events_for_response() if e.get("sport", "").lower() == sport_key]


@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске приложения"""
    events_24h = _collect_events_for_response()
    logger.info("🚀 PRIZOLOV SPORTS AI v13.0 - LIVE + 24H ЗАПУЩЕН")
    logger.info(f"📊 Событий с проходными ставками в 24ч: {len(events_24h)}")

    sports_count = _sports_line(events_24h)
    for sport, count in sports_count.items():
        logger.info(f"  ⚽ {sport.upper()}: {count} событий")


@app.get("/")
async def root():
    events_24h = _collect_events_for_response()
    return {
        "status": "online",
        "version": "13.0",
        "total_events_24h": len(events_24h),
        "sports_24h": len(_sports_line(events_24h)),
    }


@app.get("/health")
async def health():
    events_24h = _collect_events_for_response()
    return {
        "status": "ok",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_events_24h": len(events_24h),
    }


@app.post("/api/state")
async def get_state(request: Request = None):
    """Получить состояние текущего анализа (LIVE + ближайшие N часов)."""
    payload = await _read_json_payload(request)
    window_hours = _coerce_int(payload.get("window_hours"), DEFAULT_WINDOW_HOURS, minimum=1, maximum=72)
    include_live = _safe_bool(payload.get("include_live"), True)
    min_probability = _coerce_float(payload.get("min_probability"), DEFAULT_MIN_PROBABILITY, minimum=0.0, maximum=1.0)
    min_coefficient = _coerce_float(payload.get("min_coefficient"), DEFAULT_MIN_COEFFICIENT, minimum=1.0, maximum=20.0)
    passable_only = _safe_bool(payload.get("passable_only"), True)
    event_index = _coerce_int(payload.get("event_index"), 0, minimum=0)

    events = _collect_events_for_response(
        window_hours=window_hours,
        include_live=include_live,
        min_probability=min_probability,
        min_coefficient=min_coefficient,
        passable_only=passable_only,
    )

    logger.debug(f"🔍 /api/state | Events in window: {len(events)}")

    if not events:
        logger.warning("⚠️ Нет событий в выбранном временном окне")
        return {
            "match_info": {"league": "—", "home": "—", "away": "—", "status": "—"},
            "recommendations": [],
            "meta": {"window_hours": window_hours, "sports_line": []},
        }

    event = events[event_index % len(events)]
    response = _build_match_payload(event)
    response["meta"] = {
        "window_hours": window_hours,
        "total_events": len(events),
        "sports_line": list(_sports_line(events).keys()),
        "min_probability": min_probability,
        "min_coefficient": min_coefficient,
    }
    logger.info(f"✅ /api/state: {event['home']} vs {event['away']} | recs: {len(response['recommendations'])}")
    return response


@app.post("/get-ai-sports.php")
async def get_ai_sports(request: Request = None):
    """Endpoint для frontend виджета (поддержка get_all + event_index)."""
    payload = await _read_json_payload(request)
    get_all = _safe_bool(payload.get("get_all"), False)

    window_hours = _coerce_int(payload.get("window_hours"), DEFAULT_WINDOW_HOURS, minimum=1, maximum=72)
    include_live = _safe_bool(payload.get("include_live"), True)
    min_probability = _coerce_float(payload.get("min_probability"), DEFAULT_MIN_PROBABILITY, minimum=0.0, maximum=1.0)
    min_coefficient = _coerce_float(payload.get("min_coefficient"), DEFAULT_MIN_COEFFICIENT, minimum=1.0, maximum=20.0)
    passable_only = _safe_bool(payload.get("passable_only"), True)
    event_index = _coerce_int(payload.get("event_index"), 0, minimum=0)
    sort_by = str(payload.get("sort_by") or "passability").lower()

    events = _collect_events_for_response(
        window_hours=window_hours,
        include_live=include_live,
        min_probability=min_probability,
        min_coefficient=min_coefficient,
        passable_only=passable_only,
        sort_by=sort_by,
    )

    sports_line = _sports_line(events)

    if get_all:
        return {
            "total": len(events),
            "events": events,
            "window_hours": window_hours,
            "sports": sports_line,
            "filters": {
                "include_live": include_live,
                "min_probability": min_probability,
                "min_coefficient": min_coefficient,
                "passable_only": passable_only,
                "sort_by": sort_by,
            },
        }

    if not events:
        return {
            "match_info": {"league": "—", "home": "—", "away": "—", "status": "—"},
            "recommendations": [],
            "meta": {"window_hours": window_hours, "sports_line": []},
        }

    event = events[event_index % len(events)]
    response = _build_match_payload(event)
    response["meta"] = {
        "window_hours": window_hours,
        "total_events": len(events),
        "sports_line": list(sports_line.keys()),
    }
    return response


@app.get("/api/all-events")
async def get_all_events(
    window_hours: int = DEFAULT_WINDOW_HOURS,
    include_live: bool = True,
    min_probability: float = DEFAULT_MIN_PROBABILITY,
    min_coefficient: float = DEFAULT_MIN_COEFFICIENT,
    passable_only: bool = True,
    sort_by: str = "passability",
):
    """Получить события в окне (по умолчанию LIVE + ближайшие 24 часа)."""
    normalized_window = _coerce_int(window_hours, DEFAULT_WINDOW_HOURS, minimum=1, maximum=72)
    normalized_probability = _coerce_float(min_probability, DEFAULT_MIN_PROBABILITY, minimum=0.0, maximum=1.0)
    normalized_coefficient = _coerce_float(min_coefficient, DEFAULT_MIN_COEFFICIENT, minimum=1.0, maximum=20.0)

    events = _collect_events_for_response(
        window_hours=normalized_window,
        include_live=include_live,
        min_probability=normalized_probability,
        min_coefficient=normalized_coefficient,
        passable_only=passable_only,
        sort_by=sort_by,
    )

    sports_map = _sports_line(events)
    return {
        "total": len(events),
        "events": events,
        "window_hours": normalized_window,
        "sports": sports_map,
        "sports_line": list(sports_map.keys()),
        "filters": {
            "include_live": include_live,
            "min_probability": normalized_probability,
            "min_coefficient": normalized_coefficient,
            "passable_only": passable_only,
            "sort_by": sort_by,
        },
    }


@app.get("/api/events/{sport}")
async def get_events_by_sport(
    sport: str,
    window_hours: int = DEFAULT_WINDOW_HOURS,
    include_live: bool = True,
    min_probability: float = DEFAULT_MIN_PROBABILITY,
    min_coefficient: float = DEFAULT_MIN_COEFFICIENT,
    passable_only: bool = True,
):
    """Получить события по виду спорта в окне ближайших часов."""
    all_events = _collect_events_for_response(
        window_hours=_coerce_int(window_hours, DEFAULT_WINDOW_HOURS, minimum=1, maximum=72),
        include_live=include_live,
        min_probability=_coerce_float(min_probability, DEFAULT_MIN_PROBABILITY, minimum=0.0, maximum=1.0),
        min_coefficient=_coerce_float(min_coefficient, DEFAULT_MIN_COEFFICIENT, minimum=1.0, maximum=20.0),
        passable_only=passable_only,
    )
    matches = [e for e in all_events if e.get("sport", "").lower() == sport.lower()]
    return {
        "sport": sport,
        "total": len(matches),
        "events": matches,
    }


@app.get("/api/sports")
async def get_sports_list(
    window_hours: int = DEFAULT_WINDOW_HOURS,
    include_live: bool = True,
    min_probability: float = DEFAULT_MIN_PROBABILITY,
    min_coefficient: float = DEFAULT_MIN_COEFFICIENT,
):
    """Получить расширенную линию видов спорта с проходными ставками."""
    events = _collect_events_for_response(
        window_hours=_coerce_int(window_hours, DEFAULT_WINDOW_HOURS, minimum=1, maximum=72),
        include_live=include_live,
        min_probability=_coerce_float(min_probability, DEFAULT_MIN_PROBABILITY, minimum=0.0, maximum=1.0),
        min_coefficient=_coerce_float(min_coefficient, DEFAULT_MIN_COEFFICIENT, minimum=1.0, maximum=20.0),
        passable_only=True,
    )
    sports = _sports_line(events)

    return {
        "sports": sports,
        "sports_line": list(sports.keys()),
        "total_events": len(events),
        "window_hours": _coerce_int(window_hours, DEFAULT_WINDOW_HOURS, minimum=1, maximum=72),
    }


@app.get("/api/debug")
async def debug_info():
    """Полная диагностика системы"""
    events = _collect_events_for_response(passable_only=False)
    return {
        "version": "13.0",
        "total_events_24h": len(events),
        "sample_events": events[:3],
        "sports_line": list(_sports_line(_filter_and_rank_events(events)).keys()),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    import uvicorn
    target_port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=target_port)
