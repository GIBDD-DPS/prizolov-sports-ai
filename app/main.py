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
from fastapi import FastAPI, Query, Request
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


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return float(default)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return int(default)


DEFAULT_PREMIUM_MIN_EDGE = _env_float("PREMIUM_MIN_EDGE", 0.08)
DEFAULT_PREMIUM_MIN_BOOKMAKERS_SUPPORT = _env_int("PREMIUM_MIN_BOOKMAKERS_SUPPORT", 4)
DEFAULT_MAX_RECOMMENDATIONS_PER_EVENT = _env_int("MAX_RECOMMENDATIONS_PER_EVENT", 6)

def _compute_edge(probability: float, coefficient: float) -> float:
    return round((probability * coefficient) - 1.0, 4)


def _estimate_bookmakers_support(rec: dict) -> int:
    confidence = str(rec.get("confidence", "med")).lower()
    base_support = {"high": 4, "med": 3, "low": 2}.get(confidence, 3)
    probability = float(rec.get("probability", 0.0) or 0.0)
    coefficient = float(rec.get("coefficient", 0.0) or 0.0)
    if probability >= 0.8:
        base_support += 1
    if coefficient >= 1.9:
        base_support += 1
    return max(base_support, 1)


def _normalize_recommendation(
    recommendation: dict,
    min_edge: float,
    min_bookmakers_support: int,
) -> dict:
    probability = float(recommendation.get("probability", 0.0) or 0.0)
    coefficient = float(recommendation.get("coefficient", 0.0) or 0.0)
    edge_raw = recommendation.get("edge")
    if edge_raw is None:
        edge = _compute_edge(probability, coefficient)
    else:
        edge = round(float(edge_raw), 4)

    support_raw = recommendation.get("bookmakers_support")
    if support_raw is None:
        bookmakers_support = _estimate_bookmakers_support(recommendation)
    else:
        bookmakers_support = max(int(support_raw), 1)

    is_premium = edge >= min_edge and bookmakers_support >= min_bookmakers_support
    selection_tier = "premium" if is_premium else recommendation.get("selection_tier", "standard")

    return {
        "line": recommendation.get("line", ""),
        "coefficient": coefficient,
        "probability": probability,
        "confidence": recommendation.get("confidence", "med"),
        "edge": edge,
        "bookmakers_support": bookmakers_support,
        "value_score": round(edge * bookmakers_support, 4),
        "is_premium": is_premium,
        "selection_tier": selection_tier,
    }


def _transform_event(
    event: dict,
    premium_only: bool,
    min_edge: float,
    min_bookmakers_support: int,
    max_recommendations_per_event: int,
) -> dict:
    normalized_recommendations = [
        _normalize_recommendation(rec, min_edge=min_edge, min_bookmakers_support=min_bookmakers_support)
        for rec in event.get("recommendations", [])
    ]
    normalized_recommendations.sort(
        key=lambda rec: (
            rec["is_premium"],
            rec["value_score"],
            rec["edge"],
            rec["probability"],
            rec["bookmakers_support"],
        ),
        reverse=True,
    )

    premium_recommendations_count = sum(1 for rec in normalized_recommendations if rec["is_premium"])
    if premium_only:
        normalized_recommendations = [rec for rec in normalized_recommendations if rec["is_premium"]]

    normalized_recommendations = normalized_recommendations[: max(max_recommendations_per_event, 1)]
    transformed = dict(event)
    transformed["recommendations"] = normalized_recommendations
    transformed["recommendations_count"] = len(normalized_recommendations)
    transformed["premium_recommendations_count"] = (
        len(normalized_recommendations) if premium_only else premium_recommendations_count
    )
    transformed["has_premium_lines"] = premium_recommendations_count > 0
    if normalized_recommendations:
        transformed["top_recommendation"] = normalized_recommendations[0]
    return transformed


def _prepare_events(
    events: list[dict],
    premium_only: bool,
    min_edge: float,
    min_bookmakers_support: int,
    max_recommendations_per_event: int,
    sport: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    prepared = []
    for event in events:
        if sport and event.get("sport") != sport:
            continue
        transformed = _transform_event(
            event=event,
            premium_only=premium_only,
            min_edge=min_edge,
            min_bookmakers_support=min_bookmakers_support,
            max_recommendations_per_event=max_recommendations_per_event,
        )
        if premium_only and not transformed.get("recommendations"):
            continue
        prepared.append(transformed)

    prepared.sort(
        key=lambda item: (
            item.get("premium_recommendations_count", 0),
            item.get("recommendations_count", 0),
            item.get("top_recommendation", {}).get("value_score", -9999.0),
        ),
        reverse=True,
    )
    if limit is not None and limit > 0:
        return prepared[:limit]
    return prepared


def _build_filters_payload(
    premium_only: bool,
    min_edge: float,
    min_bookmakers_support: int,
    max_recommendations_per_event: int,
) -> dict:
    return {
        "premium_only": premium_only,
        "min_edge": min_edge,
        "min_bookmakers_support": min_bookmakers_support,
        "max_recommendations_per_event": max_recommendations_per_event,
    }


def _feature_flags() -> dict:
    return {
        "premium_lines_mode": True,
        "edge_scoring": True,
        "bookmakers_support": True,
    }


def get_all_live_matches() -> list[dict]:
    """Получить все live матчи."""
    return LIVE_EVENTS


def get_matches_by_sport(sport: str) -> list[dict]:
    """Получить матчи по виду спорта."""
    return [event for event in LIVE_EVENTS if event["sport"] == sport]


@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске приложения."""
    logger.info("🚀 PRIZOLOV SPORTS AI v12.0 LIVE SPORTS - ЗАПУЩЕН")
    logger.info(f"📊 Всего live событий: {len(LIVE_EVENTS)}")
    logger.info(
        "🎯 Premium filters: min_edge=%.3f min_support=%d max_recs=%d",
        DEFAULT_PREMIUM_MIN_EDGE,
        DEFAULT_PREMIUM_MIN_BOOKMAKERS_SUPPORT,
        DEFAULT_MAX_RECOMMENDATIONS_PER_EVENT,
    )

    sports_count = {}
    for event in LIVE_EVENTS:
        sport = event["sport"]
        sports_count[sport] = sports_count.get(sport, 0) + 1

    for sport, count in sports_count.items():
        logger.info(f"  ⚽ {sport.upper()}: {count} матчей")


@app.get("/")
async def root():
    return {
        "status": "online",
        "version": "12.0",
        "total_live_events": len(LIVE_EVENTS),
        "features": _feature_flags(),
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_events": len(LIVE_EVENTS),
    }


@app.get("/api/source-status")
async def source_status():
    return {
        "status": "ok",
        "source": "live_events_static_seed",
        "events_total": len(LIVE_EVENTS),
        "quality_filters": {
            "premium_min_edge": DEFAULT_PREMIUM_MIN_EDGE,
            "premium_min_bookmakers_support": DEFAULT_PREMIUM_MIN_BOOKMAKERS_SUPPORT,
            "max_recommendations_per_event": DEFAULT_MAX_RECOMMENDATIONS_PER_EVENT,
        },
        "features": _feature_flags(),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


@app.post("/api/state")
async def get_state(
    request: Request = None,
    premium_only: bool = Query(False),
    min_edge: float = Query(DEFAULT_PREMIUM_MIN_EDGE),
    min_bookmakers_support: int = Query(DEFAULT_PREMIUM_MIN_BOOKMAKERS_SUPPORT, ge=1),
    max_recommendations_per_event: int = Query(DEFAULT_MAX_RECOMMENDATIONS_PER_EVENT, ge=1, le=20),
):
    """Получить состояние текущего анализа."""
    prepared_events = _prepare_events(
        events=LIVE_EVENTS,
        premium_only=premium_only,
        min_edge=min_edge,
        min_bookmakers_support=min_bookmakers_support,
        max_recommendations_per_event=max_recommendations_per_event,
    )

    if not prepared_events:
        logger.warning("⚠️ Нет live событий под заданные фильтры")
        return {
            "match_info": {"league": "—", "home": "—", "away": "—", "status": "—"},
            "recommendations": [],
            "filters": _build_filters_payload(
                premium_only=premium_only,
                min_edge=min_edge,
                min_bookmakers_support=min_bookmakers_support,
                max_recommendations_per_event=max_recommendations_per_event,
            ),
            "features": _feature_flags(),
        }

    event = prepared_events[0]
    recommendations = []
    for rec in event.get("recommendations", []):
        recommendations.append(
            {
                "league": event["league"],
                "sport": event["sport"],
                "home": event["home"],
                "away": event["away"],
                "line": rec["line"],
                "confidence": rec["confidence"],
                "probability": rec["probability"],
                "coefficient": rec["coefficient"],
                "edge": rec["edge"],
                "bookmakers_support": rec["bookmakers_support"],
                "value_score": rec["value_score"],
                "is_premium": rec["is_premium"],
                "selection_tier": rec["selection_tier"],
            }
        )

    logger.info(
        "✅ Возвращаю %d рекомендаций для %s vs %s | premium_only=%s",
        len(recommendations),
        event["home"],
        event["away"],
        premium_only,
    )

    return {
        "match_info": {
            "league": event["league"],
            "home": event["home"],
            "away": event["away"],
            "status": f"{event['time']} ({event['score']})",
            "sport": event["sport"],
            "premium_only": premium_only,
        },
        "recommendations": recommendations,
        "filters": _build_filters_payload(
            premium_only=premium_only,
            min_edge=min_edge,
            min_bookmakers_support=min_bookmakers_support,
            max_recommendations_per_event=max_recommendations_per_event,
        ),
        "features": _feature_flags(),
    }


@app.post("/get-ai-sports.php")
async def get_ai_sports(
    request: Request = None,
    premium_only: bool = Query(False),
    min_edge: float = Query(DEFAULT_PREMIUM_MIN_EDGE),
    min_bookmakers_support: int = Query(DEFAULT_PREMIUM_MIN_BOOKMAKERS_SUPPORT, ge=1),
    max_recommendations_per_event: int = Query(DEFAULT_MAX_RECOMMENDATIONS_PER_EVENT, ge=1, le=20),
):
    """Endpoint для frontend виджета."""
    return await get_state(
        request=request,
        premium_only=premium_only,
        min_edge=min_edge,
        min_bookmakers_support=min_bookmakers_support,
        max_recommendations_per_event=max_recommendations_per_event,
    )


@app.get("/api/all-events")
async def get_all_events(
    premium_only: bool = Query(False),
    min_edge: float = Query(DEFAULT_PREMIUM_MIN_EDGE),
    min_bookmakers_support: int = Query(DEFAULT_PREMIUM_MIN_BOOKMAKERS_SUPPORT, ge=1),
    max_recommendations_per_event: int = Query(DEFAULT_MAX_RECOMMENDATIONS_PER_EVENT, ge=1, le=20),
    limit: int = Query(0, ge=0, le=200),
):
    """Получить все live события."""
    prepared_events = _prepare_events(
        events=LIVE_EVENTS,
        premium_only=premium_only,
        min_edge=min_edge,
        min_bookmakers_support=min_bookmakers_support,
        max_recommendations_per_event=max_recommendations_per_event,
        limit=limit if limit > 0 else None,
    )
    return {
        "total": len(prepared_events),
        "events": prepared_events,
        "filters": _build_filters_payload(
            premium_only=premium_only,
            min_edge=min_edge,
            min_bookmakers_support=min_bookmakers_support,
            max_recommendations_per_event=max_recommendations_per_event,
        ),
        "features": _feature_flags(),
    }


@app.get("/api/events/{sport}")
async def get_events_by_sport(
    sport: str,
    premium_only: bool = Query(False),
    min_edge: float = Query(DEFAULT_PREMIUM_MIN_EDGE),
    min_bookmakers_support: int = Query(DEFAULT_PREMIUM_MIN_BOOKMAKERS_SUPPORT, ge=1),
    max_recommendations_per_event: int = Query(DEFAULT_MAX_RECOMMENDATIONS_PER_EVENT, ge=1, le=20),
):
    """Получить события по виду спорта."""
    matches = _prepare_events(
        events=LIVE_EVENTS,
        premium_only=premium_only,
        min_edge=min_edge,
        min_bookmakers_support=min_bookmakers_support,
        max_recommendations_per_event=max_recommendations_per_event,
        sport=sport.lower(),
    )
    return {
        "sport": sport,
        "total": len(matches),
        "events": matches,
        "filters": _build_filters_payload(
            premium_only=premium_only,
            min_edge=min_edge,
            min_bookmakers_support=min_bookmakers_support,
            max_recommendations_per_event=max_recommendations_per_event,
        ),
        "features": _feature_flags(),
    }


@app.get("/api/recommendations/top")
async def get_top_recommendations(
    premium_only: bool = Query(True),
    min_edge: float = Query(DEFAULT_PREMIUM_MIN_EDGE),
    min_bookmakers_support: int = Query(DEFAULT_PREMIUM_MIN_BOOKMAKERS_SUPPORT, ge=1),
    max_recommendations_per_event: int = Query(DEFAULT_MAX_RECOMMENDATIONS_PER_EVENT, ge=1, le=20),
    limit: int = Query(20, ge=1, le=200),
):
    prepared_events = _prepare_events(
        events=LIVE_EVENTS,
        premium_only=premium_only,
        min_edge=min_edge,
        min_bookmakers_support=min_bookmakers_support,
        max_recommendations_per_event=max_recommendations_per_event,
    )
    flat_recommendations = []
    for event in prepared_events:
        for rec in event.get("recommendations", []):
            if premium_only and not rec.get("is_premium"):
                continue
            flat_recommendations.append(
                {
                    "event_id": event.get("id"),
                    "sport": event.get("sport"),
                    "league": event.get("league"),
                    "home": event.get("home"),
                    "away": event.get("away"),
                    **rec,
                }
            )

    flat_recommendations.sort(
        key=lambda rec: (
            rec["is_premium"],
            rec["value_score"],
            rec["edge"],
            rec["probability"],
            rec["bookmakers_support"],
        ),
        reverse=True,
    )
    flat_recommendations = flat_recommendations[:limit]

    return {
        "total": len(flat_recommendations),
        "recommendations": flat_recommendations,
        "filters": _build_filters_payload(
            premium_only=premium_only,
            min_edge=min_edge,
            min_bookmakers_support=min_bookmakers_support,
            max_recommendations_per_event=max_recommendations_per_event,
        ),
        "features": _feature_flags(),
    }


@app.get("/api/sports")
async def get_sports_list(
    premium_only: bool = Query(False),
    min_edge: float = Query(DEFAULT_PREMIUM_MIN_EDGE),
    min_bookmakers_support: int = Query(DEFAULT_PREMIUM_MIN_BOOKMAKERS_SUPPORT, ge=1),
    max_recommendations_per_event: int = Query(DEFAULT_MAX_RECOMMENDATIONS_PER_EVENT, ge=1, le=20),
):
    """Получить список видов спорта."""
    prepared_events = _prepare_events(
        events=LIVE_EVENTS,
        premium_only=premium_only,
        min_edge=min_edge,
        min_bookmakers_support=min_bookmakers_support,
        max_recommendations_per_event=max_recommendations_per_event,
    )
    sports = {}
    for event in prepared_events:
        sport = event["sport"]
        if sport not in sports:
            sports[sport] = 0
        sports[sport] += 1

    return {
        "sports": sports,
        "total_events": len(prepared_events),
        "filters": _build_filters_payload(
            premium_only=premium_only,
            min_edge=min_edge,
            min_bookmakers_support=min_bookmakers_support,
            max_recommendations_per_event=max_recommendations_per_event,
        ),
        "features": _feature_flags(),
    }


@app.get("/api/debug")
async def debug_info():
    """Полная диагностика системы."""
    sample_events = _prepare_events(
        events=LIVE_EVENTS[:3],
        premium_only=False,
        min_edge=DEFAULT_PREMIUM_MIN_EDGE,
        min_bookmakers_support=DEFAULT_PREMIUM_MIN_BOOKMAKERS_SUPPORT,
        max_recommendations_per_event=DEFAULT_MAX_RECOMMENDATIONS_PER_EVENT,
    )
    return {
        "version": "12.0",
        "total_live_events": len(LIVE_EVENTS),
        "sample_events": sample_events,
        "features": _feature_flags(),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    import uvicorn

    target_port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=target_port)
