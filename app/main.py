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
import json
from threading import Lock
from typing import Any, Dict, List, Optional
import aiohttp
from fastapi import FastAPI, HTTPException, Request
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

REAL_EVENTS_CACHE_TTL_SECONDS = int(os.environ.get("REAL_EVENTS_CACHE_TTL_SECONDS", "90"))
RUNTIME_EVENTS_CACHE: Dict[str, Any] = {"ts": 0.0, "events": [], "source": "unknown"}
REAL_SOURCE_STATUS: Dict[str, Any] = {
    "last_fetch_at": None,
    "last_fetch_ok": False,
    "last_http_status": None,
    "last_error": None,
    "last_count": 0,
    "last_input_count": 0,
    "last_filtered_out": 0,
    "adaptive_enabled": False,
    "adaptive_min_probability": None,
    "adaptive_min_probability_base": None,
    "adaptive_adjustments": [],
    "adaptive_feedback_used": 0,
    "used_fallback": True,
    "active_source": "demo_fallback",
    "cache_hit": False,
}
ODDS_API_UPCOMING_URL = "https://api.the-odds-api.com/v4/sports/upcoming/odds/"

SPORT_LABELS: Dict[str, Dict[str, str]] = {
    "football": {"ru": "Футбол", "en": "Football"},
    "hockey": {"ru": "Хоккей", "en": "Hockey"},
    "basketball": {"ru": "Баскетбол", "en": "Basketball"},
    "tennis": {"ru": "Теннис", "en": "Tennis"},
    "volleyball": {"ru": "Волейбол", "en": "Volleyball"},
    "handball": {"ru": "Гандбол", "en": "Handball"},
    "esports": {"ru": "Киберспорт", "en": "Esports"},
    "mma": {"ru": "ММА", "en": "MMA"},
    "baseball": {"ru": "Бейсбол", "en": "Baseball"},
    "cricket": {"ru": "Крикет", "en": "Cricket"},
    "americanfootball": {"ru": "Американский футбол", "en": "American Football"},
    "other": {"ru": "Другой спорт", "en": "Other Sport"},
}


SELF_LEARNING_ENABLED = os.environ.get("SELF_LEARNING_ENABLED", "1").strip().lower() not in {"0", "false", "no", "off"}
SELF_LEARNING_STATE_PATH = os.environ.get("SELF_LEARNING_STATE_PATH", "runtime/self_learning_state.json")
SELF_LEARNING_MIN_FEEDBACK = int(os.environ.get("SELF_LEARNING_MIN_FEEDBACK", "8"))
SELF_LEARNING_MAX_FACTOR_SHIFT = float(os.environ.get("SELF_LEARNING_MAX_FACTOR_SHIFT", "0.25"))
SELF_LEARNING_HISTORY_LIMIT = max(20, int(os.environ.get("SELF_LEARNING_HISTORY_LIMIT", "300")))
SELF_LEARNING_STATE: Dict[str, Any] = {
    "updated_at": None,
    "total_feedback": 0,
    "sports": {},
    "recent_feedback": [],
}
SELF_LEARNING_LOCK = Lock()

SUPPORTED_RUNTIME_SPORTS = {
    sport.strip().lower()
    for sport in os.environ.get(
        "SUPPORTED_RUNTIME_SPORTS",
        "football,hockey,basketball,tennis,volleyball,handball,esports,mma",
    ).split(",")
    if sport.strip()
}
MIN_BOOKMAKERS_PER_EVENT = max(1, int(os.environ.get("MIN_BOOKMAKERS_PER_EVENT", "2")))
MIN_RECOMMENDATION_PROBABILITY = min(0.9, max(0.01, float(os.environ.get("MIN_RECOMMENDATION_PROBABILITY", "0.46"))))
MIN_RECOMMENDATION_COEFFICIENT = max(1.01, float(os.environ.get("MIN_RECOMMENDATION_COEFFICIENT", "1.55")))
MIN_RECOMMENDATION_EDGE = max(-0.15, min(0.3, float(os.environ.get("MIN_RECOMMENDATION_EDGE", "0.015"))))
MAX_RECOMMENDATIONS_PER_EVENT = max(1, int(os.environ.get("MAX_RECOMMENDATIONS_PER_EVENT", "6")))
MAX_LINES_PER_MARKET = max(1, int(os.environ.get("MAX_LINES_PER_MARKET", "3")))
REAL_EVENTS_MAX_UPCOMING_HOURS = max(1, int(os.environ.get("REAL_EVENTS_MAX_UPCOMING_HOURS", "72")))
MIN_EVENT_QUALITY_SCORE = min(100.0, max(0.0, float(os.environ.get("MIN_EVENT_QUALITY_SCORE", "42"))))

ADAPTIVE_THRESHOLD_ENABLED = os.environ.get("ADAPTIVE_THRESHOLD_ENABLED", "1").strip().lower() not in {"0", "false", "no", "off"}
ADAPTIVE_THRESHOLD_MIN_FEEDBACK = max(1, int(os.environ.get("ADAPTIVE_THRESHOLD_MIN_FEEDBACK", "20")))
ADAPTIVE_MIN_PROBABILITY_FLOOR = min(0.8, max(0.01, float(os.environ.get("ADAPTIVE_MIN_PROBABILITY_FLOOR", "0.40"))))
ADAPTIVE_MIN_PROBABILITY_CEIL = min(0.95, max(ADAPTIVE_MIN_PROBABILITY_FLOOR, float(os.environ.get("ADAPTIVE_MIN_PROBABILITY_CEIL", "0.72"))))

STOREFRONT_ADAPTIVE_MODE_ENABLED = os.environ.get("STOREFRONT_ADAPTIVE_MODE_ENABLED", "1").strip().lower() not in {"0", "false", "no", "off"}
STOREFRONT_RECENT_WINDOW_HOURS = max(1, int(os.environ.get("STOREFRONT_RECENT_WINDOW_HOURS", "24")))
STOREFRONT_BASELINE_WINDOW_HOURS = max(STOREFRONT_RECENT_WINDOW_HOURS + 1, int(os.environ.get("STOREFRONT_BASELINE_WINDOW_HOURS", "168")))
STOREFRONT_ALERT_MIN_SAMPLES = max(1, int(os.environ.get("STOREFRONT_ALERT_MIN_SAMPLES", "10")))
STOREFRONT_DEGRADED_MIN_PROBABILITY = min(0.95, max(0.01, float(os.environ.get("STOREFRONT_DEGRADED_MIN_PROBABILITY", "0.62"))))
STOREFRONT_DEGRADED_MIN_QUALITY = min(100.0, max(0.0, float(os.environ.get("STOREFRONT_DEGRADED_MIN_QUALITY", "55"))))
STOREFRONT_DEGRADED_MAX_EVENTS = max(1, int(os.environ.get("STOREFRONT_DEGRADED_MAX_EVENTS", "25")))


def _normalize_lang(lang: Optional[str]) -> str:
    val = str(lang or "ru").strip().lower()
    return "en" if val.startswith("en") else "ru"


def _get_sport_labels(sport_code: Optional[str]) -> Dict[str, str]:
    code = str(sport_code or "other").lower()
    labels = SPORT_LABELS.get(code)
    if labels:
        return labels

    pretty = code.replace("_", " ").replace("-", " ").strip()
    if not pretty:
        pretty = "other"

    return {
        "ru": pretty.capitalize(),
        "en": pretty.capitalize(),
    }


def _localize_event(event: Dict[str, Any], lang: str) -> Dict[str, Any]:
    localized = dict(event)
    sport_code = str(event.get("sport", "other")).lower()
    labels = _get_sport_labels(sport_code)
    learning_meta = _get_learning_meta(sport_code)

    localized["sport_code"] = sport_code
    localized["sport_ru"] = labels["ru"]
    localized["sport_en"] = labels["en"]
    localized["sport"] = labels["ru"] if lang == "ru" else labels["en"]
    localized["learning_factor"] = learning_meta["factor"]
    localized["learning_feedback_count"] = learning_meta["feedback_count"]

    recs = []
    for rec in (event.get("recommendations") or []):
        if not isinstance(rec, dict):
            continue
        rec_local = dict(rec)
        base_probability = _normalize_probability(rec_local.get("probability", 0.5))
        adjusted_probability = _apply_learning_to_probability(base_probability, learning_meta["factor"])

        coefficient = _safe_float(rec_local.get("coefficient"), 1.5)
        rec_local["sport_code"] = sport_code
        rec_local["sport_ru"] = labels["ru"]
        rec_local["sport_en"] = labels["en"]
        rec_local["sport"] = labels["ru"] if lang == "ru" else labels["en"]
        rec_local["base_probability"] = round(base_probability, 4)
        rec_local["probability"] = round(adjusted_probability, 4)
        rec_local["learning_factor"] = learning_meta["factor"]
        rec_local["learning_feedback_count"] = learning_meta["feedback_count"]
        rec_local["confidence"] = _probability_to_confidence(adjusted_probability)
        rec_local["value_score"] = rec_local.get("value_score", _recommendation_strength(adjusted_probability, coefficient))
        rec_local["reasoning"] = rec_local.get("reasoning") or _build_recommendation_reason(localized, rec_local)
        recs.append(rec_local)

    recs.sort(
        key=lambda rec: (
            _safe_float(rec.get("value_score"), 0.0),
            _safe_float(rec.get("probability"), 0.0),
            _safe_float(rec.get("coefficient"), 0.0),
        ),
        reverse=True,
    )

    top_recommendation = recs[0] if recs else None
    top_probability = _safe_float(top_recommendation.get("probability"), 0.0) if top_recommendation else 0.0
    quality_score = _safe_float(localized.get("quality_score"), 55.0 if recs else 0.0)

    localized["recommendations"] = recs
    localized["recommendations_count"] = len(recs)
    localized["top_probability"] = round(top_probability, 4) if top_recommendation else None
    localized["top_value_score"] = round(_safe_float(top_recommendation.get("value_score"), 0.0), 4) if top_recommendation else None
    localized["display_priority"] = round((quality_score * 0.65) + (top_probability * 100.0 * 0.35), 2)
    localized["top_recommendation"] = (
        {
            "line": top_recommendation.get("line"),
            "probability": top_recommendation.get("probability"),
            "coefficient": top_recommendation.get("coefficient"),
            "confidence": top_recommendation.get("confidence"),
            "reasoning": top_recommendation.get("reasoning"),
        }
        if top_recommendation
        else None
    )

    return localized


def _localize_events(events: List[Dict[str, Any]], lang: str) -> List[Dict[str, Any]]:
    selected_lang = _normalize_lang(lang)
    return [_localize_event(event, selected_lang) for event in events]


def _build_recommendation_reason(event: Dict[str, Any], recommendation: Dict[str, Any]) -> str:
    parts: List[str] = []
    market = str(recommendation.get("market") or "").strip().upper()
    if market:
        parts.append(f"Market: {market}")

    quality_score = _safe_float(event.get("quality_score"), 0.0)
    if quality_score > 0:
        parts.append(f"Quality {quality_score:.1f}")

    freshness = str(event.get("freshness") or "").strip().lower()
    if freshness:
        parts.append(f"Freshness: {freshness}")

    probability = _safe_float(recommendation.get("probability"), 0.0)
    parts.append(f"Prob {probability:.2f}")
    return " | ".join(parts)


def _normalize_sort_by(sort_by: Optional[str]) -> str:
    normalized = str(sort_by or "priority").strip().lower()
    if normalized in {"priority", "quality", "probability", "freshness", "time", "auto"}:
        return normalized
    return "priority"


def _normalize_policy_mode(policy_mode: Optional[str]) -> str:
    normalized = str(policy_mode or "auto").strip().lower()
    if normalized in {"auto", "normal", "guarded", "degraded"}:
        return normalized
    return "auto"


def _event_sort_key(event: Dict[str, Any], sort_by: str) -> Any:
    status_weight = 0 if str(event.get("status", "")).upper() == "LIVE" else 1
    quality_score = _safe_float(event.get("quality_score"), 0.0)
    top_probability = _safe_float(event.get("top_probability"), 0.0)
    display_priority = _safe_float(event.get("display_priority"), 0.0)
    freshness_seconds = event.get("freshness_seconds")
    freshness_value = _safe_int(freshness_seconds, 10**9) if freshness_seconds is not None else 10**9

    if sort_by == "quality":
        return (status_weight, -quality_score, -top_probability, -display_priority)
    if sort_by == "probability":
        return (status_weight, -top_probability, -quality_score, -display_priority)
    if sort_by == "freshness":
        return (status_weight, freshness_value, -quality_score, -top_probability)
    if sort_by == "time":
        return (status_weight, str(event.get("time") or ""), -display_priority)
    return (status_weight, -display_priority, -quality_score, -top_probability)


def _prepare_output_events(
    events: List[Dict[str, Any]],
    sport_filter: Optional[str] = None,
    min_quality: float = 0.0,
    min_probability: float = 0.0,
    recommendations_only: bool = False,
    sort_by: str = "priority",
    limit: int = 40,
) -> List[Dict[str, Any]]:
    normalized_sport_filter = str(sport_filter or "").strip().lower()
    min_quality_clamped = _clamp(_safe_float(min_quality, 0.0), 0.0, 100.0)
    min_probability_clamped = _clamp(_safe_float(min_probability, 0.0), 0.0, 0.99)
    normalized_sort_by = _normalize_sort_by(sort_by)

    filtered: List[Dict[str, Any]] = []
    for event in events:
        if not isinstance(event, dict):
            continue

        event_sport_code = str(event.get("sport_code") or event.get("sport") or "").strip().lower()
        if normalized_sport_filter and event_sport_code != normalized_sport_filter:
            continue

        recs_raw = event.get("recommendations") or []
        recs = [rec for rec in recs_raw if isinstance(rec, dict)]
        if min_probability_clamped > 0:
            recs = [rec for rec in recs if _safe_float(rec.get("probability"), 0.0) >= min_probability_clamped]

        if recommendations_only and not recs:
            continue

        quality_score = _safe_float(event.get("quality_score"), 0.0)
        if quality_score < min_quality_clamped:
            continue

        enriched = dict(event)
        enriched["recommendations"] = recs
        enriched["recommendations_count"] = len(recs)

        top_recommendation = recs[0] if recs else None
        top_probability = _safe_float(top_recommendation.get("probability"), 0.0) if top_recommendation else 0.0
        top_value = _safe_float(top_recommendation.get("value_score"), 0.0) if top_recommendation else 0.0

        enriched["top_probability"] = round(top_probability, 4) if top_recommendation else None
        enriched["top_value_score"] = round(top_value, 4) if top_recommendation else None
        enriched["display_priority"] = round(
            (max(quality_score, _safe_float(event.get("quality_score"), 55.0 if recs else 0.0)) * 0.65)
            + (top_probability * 100.0 * 0.35),
            2,
        )
        enriched["top_recommendation"] = (
            {
                "line": top_recommendation.get("line"),
                "probability": top_recommendation.get("probability"),
                "coefficient": top_recommendation.get("coefficient"),
                "confidence": top_recommendation.get("confidence"),
                "reasoning": top_recommendation.get("reasoning"),
            }
            if top_recommendation
            else None
        )
        filtered.append(enriched)

    filtered.sort(key=lambda event: _event_sort_key(event, normalized_sort_by))
    max_limit = max(1, min(200, _safe_int(limit, 40)))
    return filtered[:max_limit]


def _build_events_meta(events: List[Dict[str, Any]], total_before_filters: int) -> Dict[str, Any]:
    sports_distribution: Dict[str, int] = {}
    live_count = 0
    quality_sum = 0.0
    quality_count = 0
    probability_sum = 0.0
    probability_count = 0

    for event in events:
        sport_code = str(event.get("sport_code") or event.get("sport") or "other").lower()
        sports_distribution[sport_code] = sports_distribution.get(sport_code, 0) + 1

        if str(event.get("status", "")).upper() == "LIVE":
            live_count += 1

        quality = event.get("quality_score")
        if quality is not None:
            quality_sum += _safe_float(quality, 0.0)
            quality_count += 1

        top_probability = event.get("top_probability")
        if top_probability is not None:
            probability_sum += _safe_float(top_probability, 0.0)
            probability_count += 1

    return {
        "total_before_filters": total_before_filters,
        "returned_events": len(events),
        "live_events": live_count,
        "sports_distribution": sports_distribution,
        "avg_quality_score": round(quality_sum / quality_count, 2) if quality_count else None,
        "avg_top_probability": round(probability_sum / probability_count, 4) if probability_count else None,
    }


def _collect_top_recommendations(
    events: List[Dict[str, Any]],
    limit: int = 10,
    min_probability: float = 0.0,
) -> List[Dict[str, Any]]:
    min_probability_clamped = _clamp(_safe_float(min_probability, 0.0), 0.0, 0.99)
    candidates: List[Dict[str, Any]] = []

    for event in events:
        if not isinstance(event, dict):
            continue
        for rec in (event.get("recommendations") or []):
            if not isinstance(rec, dict):
                continue
            probability = _safe_float(rec.get("probability"), 0.0)
            if probability < min_probability_clamped:
                continue
            candidates.append(
                {
                    "event_id": event.get("id"),
                    "league": event.get("league"),
                    "home": event.get("home"),
                    "away": event.get("away"),
                    "sport": event.get("sport"),
                    "sport_code": event.get("sport_code"),
                    "line": rec.get("line"),
                    "probability": rec.get("probability"),
                    "coefficient": rec.get("coefficient"),
                    "confidence": rec.get("confidence"),
                    "value_score": rec.get("value_score"),
                    "reasoning": rec.get("reasoning"),
                    "display_priority": event.get("display_priority"),
                    "quality_score": event.get("quality_score"),
                }
            )

    candidates.sort(
        key=lambda rec: (
            _safe_float(rec.get("value_score"), 0.0),
            _safe_float(rec.get("probability"), 0.0),
            _safe_float(rec.get("display_priority"), 0.0),
        ),
        reverse=True,
    )
    max_limit = max(1, min(100, _safe_int(limit, 10)))
    return candidates[:max_limit]


def _default_learning_sport_state() -> Dict[str, Any]:
    return {
        "feedback_count": 0,
        "hits": 0,
        "sum_predicted_probability": 0.0,
        "sum_brier_score": 0.0,
        "sum_roi": 0.0,
        "roi_count": 0,
        "last_updated": None,
    }


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _normalize_probability(value: Any) -> float:
    try:
        prob = float(value)
    except (TypeError, ValueError):
        prob = 0.5
    return _clamp(prob, 0.01, 0.99)


def _probability_to_confidence(probability: float) -> str:
    if probability >= 0.62:
        return "high"
    if probability >= 0.42:
        return "med"
    return "low"


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _save_self_learning_state_locked() -> None:
    path = pathlib.Path(SELF_LEARNING_STATE_PATH)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(SELF_LEARNING_STATE, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.warning(f"⚠️ Не удалось сохранить self-learning state: {exc}")


def _load_self_learning_state() -> None:
    if not SELF_LEARNING_ENABLED:
        return

    path = pathlib.Path(SELF_LEARNING_STATE_PATH)
    if not path.exists():
        return

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning(f"⚠️ Не удалось загрузить self-learning state: {exc}")
        return

    if not isinstance(payload, dict):
        return

    sports_payload = payload.get("sports")
    normalized_sports: Dict[str, Dict[str, Any]] = {}
    if isinstance(sports_payload, dict):
        for sport_key, stats in sports_payload.items():
            if not isinstance(stats, dict):
                continue
            sport_code = _normalize_sport_key(str(sport_key))
            normalized_sports[sport_code] = {
                "feedback_count": max(0, _safe_int(stats.get("feedback_count"), 0)),
                "hits": max(0, _safe_int(stats.get("hits"), 0)),
                "sum_predicted_probability": max(0.0, _safe_float(stats.get("sum_predicted_probability"), 0.0)),
                "sum_brier_score": max(0.0, _safe_float(stats.get("sum_brier_score"), 0.0)),
                "sum_roi": _safe_float(stats.get("sum_roi"), 0.0),
                "roi_count": max(0, _safe_int(stats.get("roi_count"), 0)),
                "last_updated": stats.get("last_updated"),
            }

    recent_feedback_payload = payload.get("recent_feedback")
    normalized_recent_feedback: List[Dict[str, Any]] = []
    if isinstance(recent_feedback_payload, list):
        for item in recent_feedback_payload[-SELF_LEARNING_HISTORY_LIMIT:]:
            if isinstance(item, dict):
                normalized_recent_feedback.append(item)

    with SELF_LEARNING_LOCK:
        SELF_LEARNING_STATE["updated_at"] = payload.get("updated_at")
        SELF_LEARNING_STATE["total_feedback"] = max(0, _safe_int(payload.get("total_feedback"), 0))
        SELF_LEARNING_STATE["sports"] = normalized_sports
        SELF_LEARNING_STATE["recent_feedback"] = normalized_recent_feedback


def _ensure_learning_stats_locked(sport_code: str) -> Dict[str, Any]:
    sport_stats = SELF_LEARNING_STATE.setdefault("sports", {}).get(sport_code)
    if not isinstance(sport_stats, dict):
        sport_stats = _default_learning_sport_state()
        SELF_LEARNING_STATE.setdefault("sports", {})[sport_code] = sport_stats
    return sport_stats


def _compute_learning_factor_from_stats(stats: Dict[str, Any]) -> float:
    feedback_count = max(0, _safe_int(stats.get("feedback_count"), 0))
    if feedback_count < SELF_LEARNING_MIN_FEEDBACK:
        return 1.0

    hits = max(0.0, _safe_float(stats.get("hits"), 0.0))
    sum_pred = max(0.0, _safe_float(stats.get("sum_predicted_probability"), 0.0))
    avg_pred = _clamp(sum_pred / max(1, feedback_count), 0.05, 0.95)
    observed_hit_rate = (hits + 1.5) / (feedback_count + 3.0)

    raw_factor = observed_hit_rate / max(0.05, avg_pred)
    min_factor = 1.0 - SELF_LEARNING_MAX_FACTOR_SHIFT
    max_factor = 1.0 + SELF_LEARNING_MAX_FACTOR_SHIFT
    return round(_clamp(raw_factor, min_factor, max_factor), 4)


def _get_learning_meta(sport_code: str) -> Dict[str, Any]:
    normalized_sport = _normalize_sport_key(sport_code)
    with SELF_LEARNING_LOCK:
        stats = SELF_LEARNING_STATE.get("sports", {}).get(normalized_sport) or _default_learning_sport_state()
        feedback_count = max(0, _safe_int(stats.get("feedback_count"), 0))
        hits = max(0, _safe_int(stats.get("hits"), 0))
        sum_pred = max(0.0, _safe_float(stats.get("sum_predicted_probability"), 0.0))
        sum_brier = max(0.0, _safe_float(stats.get("sum_brier_score"), 0.0))
        sum_roi = _safe_float(stats.get("sum_roi"), 0.0)
        roi_count = max(0, _safe_int(stats.get("roi_count"), 0))

    factor = _compute_learning_factor_from_stats(stats)
    avg_pred = round(sum_pred / feedback_count, 4) if feedback_count else None
    hit_rate = round(hits / feedback_count, 4) if feedback_count else None
    brier_score = round(sum_brier / feedback_count, 5) if feedback_count else None
    calibration_gap = round((hit_rate - avg_pred), 5) if (hit_rate is not None and avg_pred is not None) else None
    roi_avg = round(sum_roi / roi_count, 5) if roi_count else None

    return {
        "sport_code": normalized_sport,
        "factor": factor,
        "feedback_count": feedback_count,
        "hits": hits,
        "avg_predicted_probability": avg_pred,
        "hit_rate": hit_rate,
        "brier_score": brier_score,
        "calibration_gap": calibration_gap,
        "roi_avg": roi_avg,
        "roi_count": roi_count,
    }


def _apply_learning_to_probability(probability: float, factor: float) -> float:
    if not SELF_LEARNING_ENABLED:
        return _normalize_probability(probability)
    return _clamp(probability * factor, 0.01, 0.99)


def _parse_outcome(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(int(value))
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "win", "won", "hit", "success"}:
            return True
        if normalized in {"0", "false", "no", "lose", "loss", "miss", "fail", "failed"}:
            return False
    return None


def _record_learning_feedback(
    sport_code: str,
    predicted_probability: float,
    outcome: bool,
    coefficient: Optional[float] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    normalized_sport = _normalize_sport_key(sport_code)
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    probability = _normalize_probability(predicted_probability)
    actual = 1.0 if outcome else 0.0
    brier = (probability - actual) ** 2

    coefficient_value = _safe_float(coefficient, 0.0)
    roi_value: Optional[float] = None
    if coefficient_value > 1.0:
        roi_value = (coefficient_value - 1.0) if outcome else -1.0

    with SELF_LEARNING_LOCK:
        stats = _ensure_learning_stats_locked(normalized_sport)
        stats["feedback_count"] = max(0, _safe_int(stats.get("feedback_count"), 0)) + 1
        stats["hits"] = max(0, _safe_int(stats.get("hits"), 0)) + (1 if outcome else 0)
        stats["sum_predicted_probability"] = max(0.0, _safe_float(stats.get("sum_predicted_probability"), 0.0)) + probability
        stats["sum_brier_score"] = max(0.0, _safe_float(stats.get("sum_brier_score"), 0.0)) + brier
        if roi_value is not None:
            stats["sum_roi"] = _safe_float(stats.get("sum_roi"), 0.0) + roi_value
            stats["roi_count"] = max(0, _safe_int(stats.get("roi_count"), 0)) + 1
        stats["last_updated"] = now_iso

        recent_feedback = SELF_LEARNING_STATE.setdefault("recent_feedback", [])
        if not isinstance(recent_feedback, list):
            recent_feedback = []
            SELF_LEARNING_STATE["recent_feedback"] = recent_feedback

        entry = {
            "timestamp": now_iso,
            "sport": normalized_sport,
            "predicted_probability": round(probability, 4),
            "outcome": bool(outcome),
            "brier_score": round(brier, 6),
        }
        if coefficient_value > 1.0:
            entry["coefficient"] = round(coefficient_value, 4)
        if roi_value is not None:
            entry["roi"] = round(roi_value, 5)
        if isinstance(metadata, dict):
            if metadata.get("event_id"):
                entry["event_id"] = metadata.get("event_id")
            if metadata.get("line"):
                entry["line"] = metadata.get("line")
            if metadata.get("source"):
                entry["source"] = metadata.get("source")

        recent_feedback.append(entry)
        if len(recent_feedback) > SELF_LEARNING_HISTORY_LIMIT:
            del recent_feedback[:-SELF_LEARNING_HISTORY_LIMIT]

        SELF_LEARNING_STATE["total_feedback"] = max(0, _safe_int(SELF_LEARNING_STATE.get("total_feedback"), 0)) + 1
        SELF_LEARNING_STATE["updated_at"] = now_iso

        _save_self_learning_state_locked()

    return _get_learning_meta(normalized_sport)


def _get_recent_feedback(limit: int = 20) -> List[Dict[str, Any]]:
    max_limit = max(1, min(200, _safe_int(limit, 20)))
    with SELF_LEARNING_LOCK:
        recent = SELF_LEARNING_STATE.get("recent_feedback") or []
        if not isinstance(recent, list):
            return []
        tail = recent[-max_limit:]
    return list(reversed([entry for entry in tail if isinstance(entry, dict)]))


def _compute_feedback_metrics(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    samples = 0
    hits = 0
    sum_probability = 0.0
    sum_brier = 0.0
    sum_roi = 0.0
    roi_count = 0

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        probability = _normalize_probability(entry.get("predicted_probability", 0.5))
        outcome = bool(entry.get("outcome"))
        brier = _safe_float(entry.get("brier_score"), (probability - (1.0 if outcome else 0.0)) ** 2)

        samples += 1
        hits += 1 if outcome else 0
        sum_probability += probability
        sum_brier += max(0.0, brier)

        if entry.get("roi") is not None:
            sum_roi += _safe_float(entry.get("roi"), 0.0)
            roi_count += 1

    if samples == 0:
        return {
            "samples": 0,
            "hit_rate": None,
            "avg_predicted_probability": None,
            "brier_score": None,
            "calibration_gap": None,
            "roi_avg": None,
            "roi_count": 0,
        }

    hit_rate = hits / samples
    avg_pred = sum_probability / samples
    brier_score = sum_brier / samples
    calibration_gap = hit_rate - avg_pred
    roi_avg = (sum_roi / roi_count) if roi_count else None

    return {
        "samples": samples,
        "hit_rate": round(hit_rate, 6),
        "avg_predicted_probability": round(avg_pred, 6),
        "brier_score": round(brier_score, 6),
        "calibration_gap": round(calibration_gap, 6),
        "roi_avg": round(roi_avg, 6) if roi_avg is not None else None,
        "roi_count": roi_count,
    }


def _compute_learning_windows(
    recent_feedback: List[Dict[str, Any]],
    recent_window_hours: int,
    baseline_window_hours: int,
) -> Dict[str, Any]:
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    recent_hours = max(1, _safe_int(recent_window_hours, 24))
    baseline_hours = max(recent_hours + 1, _safe_int(baseline_window_hours, 168))

    recent_boundary = now_utc - datetime.timedelta(hours=recent_hours)
    baseline_boundary = now_utc - datetime.timedelta(hours=baseline_hours)

    recent_entries: List[Dict[str, Any]] = []
    baseline_entries: List[Dict[str, Any]] = []

    for entry in recent_feedback:
        if not isinstance(entry, dict):
            continue
        ts = _parse_iso_datetime(entry.get("timestamp"))
        if not ts:
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=datetime.timezone.utc)

        if ts >= recent_boundary:
            recent_entries.append(entry)
        elif ts >= baseline_boundary:
            baseline_entries.append(entry)

    recent_metrics = _compute_feedback_metrics(recent_entries)
    baseline_metrics = _compute_feedback_metrics(baseline_entries)

    trend: Dict[str, Optional[float]] = {}
    for key in ["hit_rate", "avg_predicted_probability", "brier_score", "calibration_gap", "roi_avg"]:
        recent_val = recent_metrics.get(key)
        baseline_val = baseline_metrics.get(key)
        if recent_val is None or baseline_val is None:
            trend[key] = None
        else:
            trend[key] = round(_safe_float(recent_val) - _safe_float(baseline_val), 6)

    return {
        "recent_window_hours": recent_hours,
        "baseline_window_hours": baseline_hours,
        "recent": recent_metrics,
        "baseline": baseline_metrics,
        "trend_delta": trend,
    }


def _build_learning_alerts(window_metrics: Dict[str, Any], min_samples: int = 10) -> List[Dict[str, Any]]:
    alerts: List[Dict[str, Any]] = []
    threshold_samples = max(1, _safe_int(min_samples, 10))

    recent = window_metrics.get("recent") or {}
    baseline = window_metrics.get("baseline") or {}
    trend = window_metrics.get("trend_delta") or {}

    recent_samples = _safe_int(recent.get("samples"), 0)
    if recent_samples < threshold_samples:
        alerts.append(
            {
                "severity": "info",
                "code": "insufficient_samples",
                "message": f"Недостаточно фидбека для стабильной оценки: {recent_samples}/{threshold_samples}",
            }
        )
        return alerts

    recent_brier = recent.get("brier_score")
    if recent_brier is not None and _safe_float(recent_brier) > 0.24:
        alerts.append(
            {
                "severity": "high",
                "code": "brier_high",
                "message": f"Brier score высокий: {recent_brier}",
            }
        )

    delta_brier = trend.get("brier_score")
    if delta_brier is not None and _safe_float(delta_brier) > 0.035:
        alerts.append(
            {
                "severity": "med",
                "code": "brier_degrading",
                "message": f"Качество ухудшилось: delta brier +{delta_brier}",
            }
        )

    calibration_gap = recent.get("calibration_gap")
    if calibration_gap is not None and abs(_safe_float(calibration_gap)) > 0.12:
        alerts.append(
            {
                "severity": "med",
                "code": "calibration_gap",
                "message": f"Сильный calibration gap: {calibration_gap}",
            }
        )

    recent_roi = recent.get("roi_avg")
    baseline_roi = baseline.get("roi_avg")
    if recent_roi is not None and _safe_float(recent_roi) < -0.12:
        alerts.append(
            {
                "severity": "med",
                "code": "roi_negative",
                "message": f"Отрицательный ROI в recent окне: {recent_roi}",
            }
        )
    elif recent_roi is not None and baseline_roi is not None and (_safe_float(recent_roi) - _safe_float(baseline_roi)) < -0.08:
        alerts.append(
            {
                "severity": "med",
                "code": "roi_drop",
                "message": f"ROI снизился относительно baseline: {recent_roi} vs {baseline_roi}",
            }
        )

    if not alerts:
        alerts.append(
            {
                "severity": "ok",
                "code": "metrics_stable",
                "message": "Метрики самообучения стабильны",
            }
        )

    return alerts



def _compute_adaptive_min_probability(status: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    base_threshold = _clamp(MIN_RECOMMENDATION_PROBABILITY, ADAPTIVE_MIN_PROBABILITY_FLOOR, ADAPTIVE_MIN_PROBABILITY_CEIL)
    if not ADAPTIVE_THRESHOLD_ENABLED:
        return {
            "enabled": False,
            "base_min_probability": round(base_threshold, 4),
            "effective_min_probability": round(base_threshold, 4),
            "delta": 0.0,
            "feedback_count_used": 0,
            "adjustments": [],
            "reason": "adaptive_disabled",
        }

    learning_status = status or _get_self_learning_status()
    feedback_count = max(0, _safe_int((learning_status or {}).get("total_feedback"), 0))
    if feedback_count < ADAPTIVE_THRESHOLD_MIN_FEEDBACK:
        return {
            "enabled": True,
            "base_min_probability": round(base_threshold, 4),
            "effective_min_probability": round(base_threshold, 4),
            "delta": 0.0,
            "feedback_count_used": feedback_count,
            "adjustments": [],
            "reason": "insufficient_feedback",
        }

    summary = (learning_status or {}).get("summary") or {}
    brier = summary.get("global_brier_score")
    calibration_gap = summary.get("global_calibration_gap")
    roi = summary.get("global_roi_avg")
    hit_rate = summary.get("global_hit_rate")

    threshold = base_threshold
    adjustments: List[Dict[str, Any]] = []

    if brier is not None:
        brier_value = _safe_float(brier)
        if brier_value > 0.24:
            threshold += 0.04
            adjustments.append({"metric": "brier", "delta": 0.04, "value": round(brier_value, 6), "rule": "high_brier"})
        elif brier_value > 0.20:
            threshold += 0.02
            adjustments.append({"metric": "brier", "delta": 0.02, "value": round(brier_value, 6), "rule": "medium_brier"})
        elif brier_value < 0.16:
            threshold -= 0.02
            adjustments.append({"metric": "brier", "delta": -0.02, "value": round(brier_value, 6), "rule": "good_brier"})

    if calibration_gap is not None:
        gap_value = abs(_safe_float(calibration_gap))
        if gap_value > 0.12:
            threshold += 0.03
            adjustments.append({"metric": "calibration_gap", "delta": 0.03, "value": round(gap_value, 6), "rule": "large_gap"})
        elif gap_value < 0.05:
            threshold -= 0.01
            adjustments.append({"metric": "calibration_gap", "delta": -0.01, "value": round(gap_value, 6), "rule": "small_gap"})

    if roi is not None:
        roi_value = _safe_float(roi)
        if roi_value < -0.08:
            threshold += 0.03
            adjustments.append({"metric": "roi", "delta": 0.03, "value": round(roi_value, 6), "rule": "negative_roi"})
        elif roi_value > 0.12:
            threshold -= 0.015
            adjustments.append({"metric": "roi", "delta": -0.015, "value": round(roi_value, 6), "rule": "strong_roi"})

    if hit_rate is not None:
        hit_value = _safe_float(hit_rate)
        if hit_value < 0.48:
            threshold += 0.015
            adjustments.append({"metric": "hit_rate", "delta": 0.015, "value": round(hit_value, 6), "rule": "low_hit_rate"})
        elif hit_value > 0.62:
            threshold -= 0.01
            adjustments.append({"metric": "hit_rate", "delta": -0.01, "value": round(hit_value, 6), "rule": "high_hit_rate"})

    effective = _clamp(threshold, ADAPTIVE_MIN_PROBABILITY_FLOOR, ADAPTIVE_MIN_PROBABILITY_CEIL)
    return {
        "enabled": True,
        "base_min_probability": round(base_threshold, 4),
        "effective_min_probability": round(effective, 4),
        "delta": round(effective - base_threshold, 4),
        "feedback_count_used": feedback_count,
        "adjustments": adjustments,
        "reason": "adaptive_from_metrics" if adjustments else "no_adjustment_needed",
    }




def _compute_storefront_policy(
    status: Dict[str, Any],
    window_metrics: Dict[str, Any],
    alerts: List[Dict[str, Any]],
    threshold_guidance: Dict[str, Any],
) -> Dict[str, Any]:
    base_policy = {
        "mode": "normal",
        "recommended_sort_by": "priority",
        "recommendations_only": False,
        "enforced_min_probability": 0.0,
        "enforced_min_quality": 0.0,
        "max_events": 200,
        "trigger_codes": [],
        "reason": "default",
    }

    if not STOREFRONT_ADAPTIVE_MODE_ENABLED:
        base_policy["reason"] = "adaptive_mode_disabled"
        return base_policy

    trigger_codes = [str(alert.get("code")) for alert in alerts if isinstance(alert, dict)]
    severe_codes = {"brier_high", "brier_degrading", "calibration_gap", "roi_negative", "roi_drop"}
    has_severe_signal = any(code in severe_codes for code in trigger_codes)

    recent = (window_metrics or {}).get("recent") or {}
    recent_samples = max(0, _safe_int(recent.get("samples"), 0))
    threshold_effective = _safe_float(threshold_guidance.get("effective_min_probability"), MIN_RECOMMENDATION_PROBABILITY)
    threshold_delta = _safe_float(threshold_guidance.get("delta"), 0.0)

    if recent_samples < STOREFRONT_ALERT_MIN_SAMPLES:
        base_policy["reason"] = "insufficient_samples"
        base_policy["trigger_codes"] = trigger_codes
        return base_policy

    if has_severe_signal or threshold_delta >= 0.03:
        enforced_prob = max(STOREFRONT_DEGRADED_MIN_PROBABILITY, threshold_effective)
        return {
            "mode": "degraded",
            "recommended_sort_by": "quality",
            "recommendations_only": True,
            "enforced_min_probability": round(_clamp(enforced_prob, 0.01, 0.99), 4),
            "enforced_min_quality": round(_clamp(STOREFRONT_DEGRADED_MIN_QUALITY, 0.0, 100.0), 2),
            "max_events": max(1, min(200, STOREFRONT_DEGRADED_MAX_EVENTS)),
            "trigger_codes": trigger_codes,
            "reason": "quality_guard_mode",
        }

    if threshold_delta >= 0.015:
        enforced_prob = max(0.55, threshold_effective)
        return {
            "mode": "guarded",
            "recommended_sort_by": "quality",
            "recommendations_only": False,
            "enforced_min_probability": round(_clamp(enforced_prob, 0.01, 0.99), 4),
            "enforced_min_quality": round(_clamp(50.0, 0.0, 100.0), 2),
            "max_events": 120,
            "trigger_codes": trigger_codes,
            "reason": "adaptive_threshold_guard",
        }

    base_policy["reason"] = "stable_metrics"
    base_policy["trigger_codes"] = trigger_codes
    return base_policy


def _apply_storefront_policy_override(
    base_policy: Dict[str, Any],
    threshold_guidance: Dict[str, Any],
    policy_mode: str,
    adaptive_policy_enabled: bool,
) -> Dict[str, Any]:
    normalized_mode = _normalize_policy_mode(policy_mode)

    if not adaptive_policy_enabled:
        policy = dict(base_policy)
        policy.update(
            {
                "mode": "normal",
                "recommended_sort_by": "priority",
                "recommendations_only": False,
                "enforced_min_probability": 0.0,
                "enforced_min_quality": 0.0,
                "max_events": 200,
                "reason": "adaptive_policy_disabled_by_request",
                "trigger_codes": policy.get("trigger_codes", []),
            }
        )
        return policy

    if normalized_mode == "auto":
        return dict(base_policy)

    threshold_effective = _safe_float(threshold_guidance.get("effective_min_probability"), MIN_RECOMMENDATION_PROBABILITY)
    mode_profiles = {
        "normal": {
            "mode": "normal",
            "recommended_sort_by": "priority",
            "recommendations_only": False,
            "enforced_min_probability": 0.0,
            "enforced_min_quality": 0.0,
            "max_events": 200,
        },
        "guarded": {
            "mode": "guarded",
            "recommended_sort_by": "quality",
            "recommendations_only": False,
            "enforced_min_probability": round(_clamp(max(0.55, threshold_effective), 0.01, 0.99), 4),
            "enforced_min_quality": 50.0,
            "max_events": 120,
        },
        "degraded": {
            "mode": "degraded",
            "recommended_sort_by": "quality",
            "recommendations_only": True,
            "enforced_min_probability": round(_clamp(max(STOREFRONT_DEGRADED_MIN_PROBABILITY, threshold_effective), 0.01, 0.99), 4),
            "enforced_min_quality": round(_clamp(STOREFRONT_DEGRADED_MIN_QUALITY, 0.0, 100.0), 2),
            "max_events": max(1, min(200, STOREFRONT_DEGRADED_MAX_EVENTS)),
        },
    }

    selected = dict(base_policy)
    selected.update(mode_profiles.get(normalized_mode, mode_profiles["normal"]))
    selected["reason"] = f"manual_policy_override_{normalized_mode}"
    return selected


def _build_storefront_context(
    status: Optional[Dict[str, Any]] = None,
    policy_mode: str = "auto",
    adaptive_policy_enabled: bool = True,
) -> Dict[str, Any]:
    learning_status = status or _get_self_learning_status()
    recent_feedback = _get_recent_feedback(limit=SELF_LEARNING_HISTORY_LIMIT)
    windows = _compute_learning_windows(
        recent_feedback=recent_feedback,
        recent_window_hours=STOREFRONT_RECENT_WINDOW_HOURS,
        baseline_window_hours=STOREFRONT_BASELINE_WINDOW_HOURS,
    )
    alerts = _build_learning_alerts(windows, min_samples=STOREFRONT_ALERT_MIN_SAMPLES)
    threshold_guidance = _compute_adaptive_min_probability(learning_status)
    base_policy = _compute_storefront_policy(
        status=learning_status,
        window_metrics=windows,
        alerts=alerts,
        threshold_guidance=threshold_guidance,
    )
    effective_policy = _apply_storefront_policy_override(
        base_policy=base_policy,
        threshold_guidance=threshold_guidance,
        policy_mode=policy_mode,
        adaptive_policy_enabled=adaptive_policy_enabled,
    )
    return {
        "windows": windows,
        "alerts": alerts,
        "threshold": threshold_guidance,
        "base_policy": base_policy,
        "policy": effective_policy,
        "policy_mode_requested": _normalize_policy_mode(policy_mode),
        "adaptive_policy_enabled": bool(adaptive_policy_enabled),
    }


def _resolve_storefront_effective_filters(
    sort_by: str,
    min_quality: float,
    min_probability: float,
    recommendations_only: bool,
    limit: int,
    storefront_policy: Dict[str, Any],
) -> Dict[str, Any]:
    requested_sort = _normalize_sort_by(sort_by)
    policy_sort = _normalize_sort_by(storefront_policy.get("recommended_sort_by", "priority"))
    effective_sort = policy_sort if requested_sort == "auto" else requested_sort
    if effective_sort == "auto":
        effective_sort = "priority"

    requested_min_quality = _clamp(_safe_float(min_quality, 0.0), 0.0, 100.0)
    requested_min_probability = _clamp(_safe_float(min_probability, 0.0), 0.0, 0.99)

    policy_min_quality = _clamp(_safe_float(storefront_policy.get("enforced_min_quality"), 0.0), 0.0, 100.0)
    policy_min_probability = _clamp(_safe_float(storefront_policy.get("enforced_min_probability"), 0.0), 0.0, 0.99)

    requested_limit = max(1, min(200, _safe_int(limit, 40)))
    policy_limit = max(1, min(200, _safe_int(storefront_policy.get("max_events"), 200)))

    return {
        "requested": {
            "sort_by": requested_sort,
            "min_quality": requested_min_quality,
            "min_probability": requested_min_probability,
            "recommendations_only": bool(recommendations_only),
            "limit": requested_limit,
        },
        "effective": {
            "sort_by": effective_sort,
            "min_quality": max(requested_min_quality, policy_min_quality),
            "min_probability": max(requested_min_probability, policy_min_probability),
            "recommendations_only": bool(recommendations_only) or bool(storefront_policy.get("recommendations_only", False)),
            "limit": min(requested_limit, policy_limit),
        },
    }



def _get_self_learning_status() -> Dict[str, Any]:
    with SELF_LEARNING_LOCK:
        total_feedback = max(0, _safe_int(SELF_LEARNING_STATE.get("total_feedback"), 0))
        updated_at = SELF_LEARNING_STATE.get("updated_at")
        sports_raw = dict(SELF_LEARNING_STATE.get("sports") or {})

    sports: Dict[str, Any] = {}
    total_hits = 0
    total_sum_pred = 0.0
    total_sum_brier = 0.0
    total_sum_roi = 0.0
    total_roi_count = 0

    for sport_code in sorted(sports_raw.keys()):
        meta = _get_learning_meta(sport_code)
        sports[sport_code] = meta

        stats = sports_raw.get(sport_code) or {}
        total_hits += max(0, _safe_int(stats.get("hits"), 0))
        total_sum_pred += max(0.0, _safe_float(stats.get("sum_predicted_probability"), 0.0))
        total_sum_brier += max(0.0, _safe_float(stats.get("sum_brier_score"), 0.0))
        total_sum_roi += _safe_float(stats.get("sum_roi"), 0.0)
        total_roi_count += max(0, _safe_int(stats.get("roi_count"), 0))

    global_hit_rate = round(total_hits / total_feedback, 4) if total_feedback else None
    global_avg_predicted = round(total_sum_pred / total_feedback, 4) if total_feedback else None
    global_brier_score = round(total_sum_brier / total_feedback, 6) if total_feedback else None
    global_calibration_gap = (
        round(global_hit_rate - global_avg_predicted, 6)
        if global_hit_rate is not None and global_avg_predicted is not None
        else None
    )
    global_roi_avg = round(total_sum_roi / total_roi_count, 6) if total_roi_count else None

    return {
        "enabled": SELF_LEARNING_ENABLED,
        "min_feedback": SELF_LEARNING_MIN_FEEDBACK,
        "max_factor_shift": SELF_LEARNING_MAX_FACTOR_SHIFT,
        "history_limit": SELF_LEARNING_HISTORY_LIMIT,
        "state_path": SELF_LEARNING_STATE_PATH,
        "total_feedback": total_feedback,
        "updated_at": updated_at,
        "summary": {
            "global_hit_rate": global_hit_rate,
            "global_avg_predicted_probability": global_avg_predicted,
            "global_brier_score": global_brier_score,
            "global_calibration_gap": global_calibration_gap,
            "global_roi_avg": global_roi_avg,
            "global_roi_count": total_roi_count,
        },
        "sports": sports,
    }


def _resolve_odds_api_key() -> Optional[str]:
    return (
        os.environ.get("THE_ODDS_API_KEY")
        or os.environ.get("API_KEYS_ODDS")
        or os.environ.get("ODDS_API_KEY")
    )


def _parse_iso_datetime(value: Optional[str]) -> Optional[datetime.datetime]:
    if not value:
        return None
    try:
        return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
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
    return dt.astimezone(datetime.timezone.utc).strftime("%H:%M UTC")


def _compute_probabilities(outcomes: List[Dict[str, Any]]) -> Dict[str, float]:
    valid = []
    for outcome in outcomes:
        try:
            price = float(outcome.get("price"))
        except (TypeError, ValueError):
            continue
        if price > 1.0:
            valid.append((outcome.get("name") or "Исход", price))

    if not valid:
        return {}

    inv_values = [(name, 1.0 / price) for name, price in valid]
    inv_sum = sum(val for _, val in inv_values)
    if inv_sum <= 0:
        return {name: 0.0 for name, _ in valid}

    probs: Dict[str, float] = {}
    for name, inv in inv_values:
        probs[name] = round(min(0.99, max(0.01, inv / inv_sum)), 4)
    return probs


def _extract_bookmaker_count(event: Dict[str, Any]) -> int:
    bookmakers = event.get("bookmakers") or []
    if not isinstance(bookmakers, list):
        return 0
    return len(bookmakers)


def _extract_freshness_seconds(event: Dict[str, Any], now_utc: datetime.datetime) -> Optional[int]:
    bookmakers = event.get("bookmakers") or []
    if not isinstance(bookmakers, list):
        return None

    latest_update: Optional[datetime.datetime] = None
    for bookmaker in bookmakers:
        if not isinstance(bookmaker, dict):
            continue
        updated = _parse_iso_datetime(bookmaker.get("last_update"))
        if not updated:
            continue
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=datetime.timezone.utc)
        if latest_update is None or updated > latest_update:
            latest_update = updated

    if not latest_update:
        return None

    delta_seconds = int((now_utc - latest_update).total_seconds())
    return max(0, delta_seconds)


def _freshness_label(freshness_seconds: Optional[int]) -> str:
    if freshness_seconds is None:
        return "unknown"
    if freshness_seconds <= 120:
        return "fresh"
    if freshness_seconds <= 600:
        return "warming"
    if freshness_seconds <= 1800:
        return "stale"
    return "outdated"


def _compute_event_quality_score(
    bookmakers_count: int,
    recommendations_count: int,
    freshness_seconds: Optional[int],
    status: str,
) -> float:
    bookmakers_factor = min(1.0, max(0.0, bookmakers_count / 6.0))
    recommendations_target = max(1, min(MAX_RECOMMENDATIONS_PER_EVENT, 4))
    recommendations_factor = min(1.0, max(0.0, recommendations_count / recommendations_target))

    freshness_factor = 0.55
    if freshness_seconds is not None:
        if freshness_seconds <= 120:
            freshness_factor = 1.0
        elif freshness_seconds <= 600:
            freshness_factor = 0.8
        elif freshness_seconds <= 1800:
            freshness_factor = 0.55
        else:
            freshness_factor = 0.25

    status_factor = 1.0 if status == "LIVE" else 0.86

    score = 100.0 * status_factor * (
        0.45 * bookmakers_factor
        + 0.35 * recommendations_factor
        + 0.20 * freshness_factor
    )
    return round(min(100.0, max(0.0, score)), 1)


def _is_event_in_supported_window(commence_dt: Optional[datetime.datetime], now_utc: datetime.datetime) -> bool:
    if not commence_dt:
        return True

    if commence_dt.tzinfo is None:
        commence_dt = commence_dt.replace(tzinfo=datetime.timezone.utc)

    max_upcoming = now_utc + datetime.timedelta(hours=REAL_EVENTS_MAX_UPCOMING_HOURS)
    too_old = now_utc - datetime.timedelta(hours=8)
    return too_old <= commence_dt <= max_upcoming


def _build_recommendation_line(market_key: str, outcome_name: str, point: Any) -> str:
    line_name = str(outcome_name or "Исход")
    if point is not None:
        line_name = f"{line_name} {point}"

    if market_key == "h2h":
        return f"H2H: {line_name}"
    if market_key == "totals":
        return f"TOTALS: {line_name}"
    if market_key == "spreads":
        return f"SPREADS: {line_name}"
    return line_name


def _recommendation_strength(probability: float, price: float) -> float:
    # Простой value-like score: вероятность и коэффициент одновременно.
    implied = min(0.99, max(0.01, 1.0 / max(price, 1.01)))
    edge = max(0.0, probability - implied)
    return round((probability * 0.7) + (edge * 0.3), 4)


def _normalize_outcome_key(outcome_name: str, point: Any) -> str:
    name = str(outcome_name or "").strip().lower()
    if point is None:
        return name
    return f"{name}|{point}"


def _build_candidate_from_group(
    group: Dict[str, Any],
    league: str,
    sport: str,
    home: str,
    away: str,
    min_probability_threshold: float,
    min_coefficient_threshold: float,
    min_edge_threshold: float,
    tier: str,
) -> Optional[Dict[str, Any]]:
    probabilities = group.get("probabilities") or []
    odds = group.get("odds") or []
    bookmakers = group.get("bookmakers") or set()

    if not probabilities or not odds:
        return None

    avg_probability = sum(probabilities) / len(probabilities)
    best_coefficient = max(odds)
    implied_probability = min(0.99, max(0.01, 1.0 / max(best_coefficient, 1.01)))
    edge = avg_probability - implied_probability

    if avg_probability < min_probability_threshold:
        return None
    if best_coefficient < min_coefficient_threshold:
        return None
    if edge < min_edge_threshold:
        return None

    coverage = len(bookmakers) if isinstance(bookmakers, set) else len(list(bookmakers))
    market_key = str(group.get("market") or "h2h")
    line = _build_recommendation_line(market_key, str(group.get("outcome_name") or "Исход"), group.get("point"))

    score = _recommendation_strength(avg_probability, best_coefficient)
    # Лёгкий бонус за подтверждение нескольких букмекеров.
    score += min(0.08, coverage * 0.01)

    return {
        "league": league,
        "sport": sport,
        "home": home,
        "away": away,
        "line": line,
        "confidence": _probability_to_confidence(avg_probability),
        "probability": round(min(0.99, max(0.01, avg_probability)), 4),
        "coefficient": round(best_coefficient, 2),
        "confidence_score": round(min(0.99, max(0.01, avg_probability)), 4),
        "market": market_key,
        "bookmaker": "consensus",
        "bookmakers_support": coverage,
        "edge": round(edge, 5),
        "value_score": round(score, 4),
        "selection_tier": tier,
    }


def _pick_diversified_recommendations(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not candidates:
        return []

    # Сначала сортируем по ценности и вероятности, потом добираем с диверсификацией рынков.
    ordered = sorted(
        candidates,
        key=lambda item: (
            _safe_float(item.get("value_score"), 0.0),
            _safe_float(item.get("probability"), 0.0),
            _safe_float(item.get("coefficient"), 0.0),
        ),
        reverse=True,
    )

    market_counts: Dict[str, int] = {}
    selected: List[Dict[str, Any]] = []

    for candidate in ordered:
        market = str(candidate.get("market") or "other")
        if market_counts.get(market, 0) >= MAX_LINES_PER_MARKET:
            continue

        selected.append(candidate)
        market_counts[market] = market_counts.get(market, 0) + 1
        if len(selected) >= MAX_RECOMMENDATIONS_PER_EVENT:
            break

    # Если из-за диверсификации выбрали меньше, чем нужно — добираем лучшими оставшимися.
    if len(selected) < MAX_RECOMMENDATIONS_PER_EVENT:
        selected_keys = {
            (
                str(item.get("market") or ""),
                str(item.get("line") or ""),
            )
            for item in selected
        }
        for candidate in ordered:
            key = (str(candidate.get("market") or ""), str(candidate.get("line") or ""))
            if key in selected_keys:
                continue
            selected.append(candidate)
            selected_keys.add(key)
            if len(selected) >= MAX_RECOMMENDATIONS_PER_EVENT:
                break

    return selected


def _extract_recommendations(event: Dict[str, Any], league: str, sport: str, home: str, away: str, min_probability_threshold: float) -> List[Dict[str, Any]]:
    recommendations: List[Dict[str, Any]] = []
    bookmakers = event.get("bookmakers") or []

    if not isinstance(bookmakers, list) or len(bookmakers) < MIN_BOOKMAKERS_PER_EVENT:
        return recommendations

    grouped_lines: Dict[str, Dict[str, Any]] = {}

    for bookmaker in bookmakers:
        if not isinstance(bookmaker, dict):
            continue
        bookmaker_name = str(bookmaker.get("title") or bookmaker.get("key") or "bookmaker")

        for market in bookmaker.get("markets") or []:
            if not isinstance(market, dict):
                continue
            market_key = str(market.get("key") or "")
            if market_key not in {"h2h", "totals", "spreads"}:
                continue

            outcomes = market.get("outcomes") or []
            if not isinstance(outcomes, list) or not outcomes:
                continue

            probabilities = _compute_probabilities(outcomes)
            for outcome in outcomes:
                if not isinstance(outcome, dict):
                    continue

                try:
                    price = float(outcome.get("price"))
                except (TypeError, ValueError):
                    continue
                if price <= 1.0:
                    continue

                outcome_name = str(outcome.get("name") or "Исход")
                point = outcome.get("point")
                probability = probabilities.get(outcome_name, round(min(0.99, 1.0 / price), 4))
                probability = max(0.01, min(0.99, probability))

                line_key = f"{market_key}:{_normalize_outcome_key(outcome_name, point)}"
                group = grouped_lines.setdefault(
                    line_key,
                    {
                        "market": market_key,
                        "outcome_name": outcome_name,
                        "point": point,
                        "probabilities": [],
                        "odds": [],
                        "bookmakers": set(),
                    },
                )

                group["probabilities"].append(probability)
                group["odds"].append(price)
                group["bookmakers"].add(bookmaker_name)

    if not grouped_lines:
        return recommendations

    strict_candidates: List[Dict[str, Any]] = []
    relaxed_candidates: List[Dict[str, Any]] = []

    strict_probability = max(min_probability_threshold, MIN_RECOMMENDATION_PROBABILITY)
    strict_coeff = max(1.01, MIN_RECOMMENDATION_COEFFICIENT)
    strict_edge = MIN_RECOMMENDATION_EDGE

    relaxed_probability = max(min_probability_threshold, strict_probability - 0.03)
    relaxed_coeff = max(1.30, strict_coeff - 0.20)
    relaxed_edge = max(-0.06, strict_edge - 0.04)

    for group in grouped_lines.values():
        strict_candidate = _build_candidate_from_group(
            group,
            league,
            sport,
            home,
            away,
            min_probability_threshold=strict_probability,
            min_coefficient_threshold=strict_coeff,
            min_edge_threshold=strict_edge,
            tier="strict",
        )
        if strict_candidate:
            strict_candidates.append(strict_candidate)
            continue

        relaxed_candidate = _build_candidate_from_group(
            group,
            league,
            sport,
            home,
            away,
            min_probability_threshold=relaxed_probability,
            min_coefficient_threshold=relaxed_coeff,
            min_edge_threshold=relaxed_edge,
            tier="relaxed",
        )
        if relaxed_candidate:
            relaxed_candidates.append(relaxed_candidate)

    candidates = strict_candidates
    if len(candidates) < max(2, MAX_RECOMMENDATIONS_PER_EVENT // 2):
        existing_keys = {
            (str(item.get("market") or ""), str(item.get("line") or ""))
            for item in candidates
        }
        for item in relaxed_candidates:
            key = (str(item.get("market") or ""), str(item.get("line") or ""))
            if key in existing_keys:
                continue
            candidates.append(item)
            existing_keys.add(key)

    return _pick_diversified_recommendations(candidates)


def _transform_odds_event(event: Dict[str, Any], now_utc: datetime.datetime, min_probability_threshold: float) -> Optional[Dict[str, Any]]:
    home = event.get("home_team")
    away = event.get("away_team")
    if not home or not away:
        return None

    sport = _normalize_sport_key(event.get("sport_key"))
    if SUPPORTED_RUNTIME_SPORTS and sport not in SUPPORTED_RUNTIME_SPORTS:
        return None

    league = event.get("sport_title") or event.get("sport_key") or "Unknown League"
    commence_time = event.get("commence_time")
    commence_dt = _parse_iso_datetime(commence_time)
    if not _is_event_in_supported_window(commence_dt, now_utc):
        return None

    status = "UPCOMING"
    if commence_dt and commence_dt <= now_utc:
        status = "LIVE"

    recommendations = _extract_recommendations(event, league, sport, home, away, min_probability_threshold=min_probability_threshold)
    if not recommendations:
        return None

    bookmakers_count = _extract_bookmaker_count(event)
    freshness_seconds = _extract_freshness_seconds(event, now_utc)
    freshness = _freshness_label(freshness_seconds)
    quality_score = _compute_event_quality_score(
        bookmakers_count=bookmakers_count,
        recommendations_count=len(recommendations),
        freshness_seconds=freshness_seconds,
        status=status,
    )

    if quality_score < MIN_EVENT_QUALITY_SCORE:
        return None

    return {
        "id": event.get("id") or f"{sport}_{home}_{away}",
        "sport": sport,
        "league": league,
        "home": home,
        "away": away,
        "status": status,
        "time": "LIVE" if status == "LIVE" else _format_event_time(commence_time),
        "score": "—",
        "bookmakers_count": bookmakers_count,
        "freshness_seconds": freshness_seconds,
        "freshness": freshness,
        "quality_score": quality_score,
        "recommendations": recommendations,
    }


async def _fetch_real_events(limit: int = 30) -> List[Dict[str, Any]]:
    api_key = _resolve_odds_api_key()
    REAL_SOURCE_STATUS["last_fetch_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    REAL_SOURCE_STATUS["cache_hit"] = False

    if not api_key:
        REAL_SOURCE_STATUS["last_fetch_ok"] = False
        REAL_SOURCE_STATUS["last_http_status"] = None
        REAL_SOURCE_STATUS["last_error"] = "missing_api_key"
        REAL_SOURCE_STATUS["last_count"] = 0
        return []

    params = {
        "apiKey": api_key,
        "regions": "eu,uk",
        "markets": "h2h,totals",
        "oddsFormat": "decimal",
        "dateFormat": "iso",
    }

    timeout = aiohttp.ClientTimeout(total=12)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(ODDS_API_UPCOMING_URL, params=params) as resp:
                if resp.status != 200:
                    REAL_SOURCE_STATUS["last_fetch_ok"] = False
                    REAL_SOURCE_STATUS["last_http_status"] = resp.status
                    REAL_SOURCE_STATUS["last_error"] = f"http_{resp.status}"
                    REAL_SOURCE_STATUS["last_count"] = 0
                    logger.warning(f"⚠️ Odds API вернул статус {resp.status}")
                    return []
                payload = await resp.json()
    except Exception as exc:
        REAL_SOURCE_STATUS["last_fetch_ok"] = False
        REAL_SOURCE_STATUS["last_http_status"] = None
        REAL_SOURCE_STATUS["last_error"] = f"request_error: {exc}"
        REAL_SOURCE_STATUS["last_count"] = 0
        logger.warning(f"⚠️ Не удалось получить реальные события из Odds API: {exc}")
        return []

    if not isinstance(payload, list):
        REAL_SOURCE_STATUS["last_fetch_ok"] = False
        REAL_SOURCE_STATUS["last_http_status"] = 200
        REAL_SOURCE_STATUS["last_error"] = "invalid_payload"
        REAL_SOURCE_STATUS["last_count"] = 0
        return []

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    learning_status = _get_self_learning_status()
    adaptive_threshold = _compute_adaptive_min_probability(learning_status)
    effective_min_probability = _safe_float(
        adaptive_threshold.get("effective_min_probability"),
        MIN_RECOMMENDATION_PROBABILITY,
    )

    events: List[Dict[str, Any]] = []
    filtered_out = 0

    for item in payload:
        if not isinstance(item, dict):
            filtered_out += 1
            continue
        transformed = _transform_odds_event(
            item,
            now_utc,
            min_probability_threshold=effective_min_probability,
        )
        if transformed:
            events.append(transformed)
        else:
            filtered_out += 1

    events.sort(
        key=lambda ev: (
            ev.get("status") != "LIVE",
            -(ev.get("quality_score") or 0),
            ev.get("time", ""),
        )
    )
    result = events[:limit]

    REAL_SOURCE_STATUS["last_fetch_ok"] = True
    REAL_SOURCE_STATUS["last_http_status"] = 200
    REAL_SOURCE_STATUS["last_error"] = None
    REAL_SOURCE_STATUS["last_input_count"] = len(payload)
    REAL_SOURCE_STATUS["last_filtered_out"] = filtered_out
    REAL_SOURCE_STATUS["last_count"] = len(result)
    REAL_SOURCE_STATUS["adaptive_enabled"] = bool(adaptive_threshold.get("enabled", False))
    REAL_SOURCE_STATUS["adaptive_min_probability"] = adaptive_threshold.get("effective_min_probability")
    REAL_SOURCE_STATUS["adaptive_min_probability_base"] = adaptive_threshold.get("base_min_probability")
    REAL_SOURCE_STATUS["adaptive_adjustments"] = adaptive_threshold.get("adjustments", [])
    REAL_SOURCE_STATUS["adaptive_feedback_used"] = adaptive_threshold.get("feedback_count_used", 0)
    return result


async def _get_runtime_events(force_refresh: bool = False) -> List[Dict[str, Any]]:
    now_ts = asyncio.get_running_loop().time()

    cached_events = RUNTIME_EVENTS_CACHE.get("events") or []
    if not force_refresh and cached_events and (now_ts - float(RUNTIME_EVENTS_CACHE.get("ts", 0.0))) < REAL_EVENTS_CACHE_TTL_SECONDS:
        source = str(RUNTIME_EVENTS_CACHE.get("source", "unknown"))
        REAL_SOURCE_STATUS["cache_hit"] = True
        REAL_SOURCE_STATUS["active_source"] = source
        REAL_SOURCE_STATUS["used_fallback"] = source != "odds_api"
        return cached_events

    real_events = await _fetch_real_events(limit=40)
    if real_events:
        RUNTIME_EVENTS_CACHE["events"] = real_events
        RUNTIME_EVENTS_CACHE["ts"] = now_ts
        RUNTIME_EVENTS_CACHE["source"] = "odds_api"
        REAL_SOURCE_STATUS["cache_hit"] = False
        REAL_SOURCE_STATUS["active_source"] = "odds_api"
        REAL_SOURCE_STATUS["used_fallback"] = False
        return real_events

    # fallback на демо-каталог, если внешний источник недоступен.
    RUNTIME_EVENTS_CACHE["events"] = LIVE_EVENTS
    RUNTIME_EVENTS_CACHE["ts"] = now_ts
    RUNTIME_EVENTS_CACHE["source"] = "demo_fallback"
    REAL_SOURCE_STATUS["cache_hit"] = False
    REAL_SOURCE_STATUS["active_source"] = "demo_fallback"
    REAL_SOURCE_STATUS["used_fallback"] = True
    return LIVE_EVENTS


def get_all_live_matches(events: Optional[List[Dict[str, Any]]] = None):
    """Получить все live матчи"""
    return events if events is not None else LIVE_EVENTS

def get_matches_by_sport(sport: str, events: Optional[List[Dict[str, Any]]] = None):
    """Получить матчи по виду спорта"""
    source = events if events is not None else LIVE_EVENTS
    return [e for e in source if str(e.get("sport", "")).lower() == sport.lower()]

def log_startup_summary():
    """Лог startup-сводки по live-событиям."""
    logger.info("🚀 PRIZOLOV SPORTS AI v12.0 LIVE SPORTS - ЗАПУЩЕН")
    logger.info(f"📊 Всего live событий: {len(LIVE_EVENTS)}")
    
    # Подсчет по видам спорта
    sports_count = {}
    for event in LIVE_EVENTS:
        sport = event["sport"]
        sports_count[sport] = sports_count.get(sport, 0) + 1
    
    for sport, count in sports_count.items():
        logger.info(f"  ⚽ {sport.upper()}: {count} матчей")

log_startup_summary()
_load_self_learning_state()


@app.get("/")
async def root():
    return {
        "status": "online",
        "version": "12.0",
        "total_live_events": len(LIVE_EVENTS),
    }


@app.get("/health")
async def health():
    events = await _get_runtime_events()
    return {
        "status": "ok",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_events": len(events),
    }


@app.post("/api/state")
async def get_state(request: Request = None):
    """Получить состояние текущего анализа"""
    payload = await _read_json_payload(request)
    lang = _normalize_lang(payload.get("lang"))
    events = await _get_runtime_events()
    logger.debug(f"🔍 Запрос /api/state | Total events: {len(events)}")
    return _build_state_response(payload, events, lang=lang)


@app.post("/get-ai-sports.php")
async def get_ai_sports(request: Request = None):
    """Endpoint для frontend виджета"""
    payload = await _read_json_payload(request)
    lang = _normalize_lang(payload.get("lang"))
    events = await _get_runtime_events()

    # Основной контракт виджета /sport/: отдаём live-события из real-source (или fallback).
    if payload.get("get_all"):
        localized_events = _localize_events(events, lang)
        logger.info(f"📦 Возвращаю полный список live событий: {len(localized_events)} | lang={lang}")
        return {
            "total": len(localized_events),
            "language": lang,
            "events": localized_events,
        }

    # Backward-compatible режим single event (для старого фронта).
    return _build_state_response(payload, events, lang=lang)


@app.get("/api/all-events")
async def get_all_events(
    lang: str = "ru",
    sport: Optional[str] = None,
    min_quality: float = 0.0,
    min_probability: float = 0.0,
    sort_by: str = "priority",
    limit: int = 40,
    recommendations_only: bool = False,
    include_top: bool = True,
    top_limit: int = 10,
    policy_mode: str = "auto",
    adaptive_policy: bool = True,
):
    """Получить все live события с фильтрами и ранжированием."""
    selected_lang = _normalize_lang(lang)
    events = await _get_runtime_events()
    localized_events = _localize_events(events, selected_lang)

    storefront_context = _build_storefront_context(policy_mode=policy_mode, adaptive_policy_enabled=adaptive_policy)
    storefront_policy = storefront_context.get("policy", {})
    filter_ctx = _resolve_storefront_effective_filters(
        sort_by=sort_by,
        min_quality=min_quality,
        min_probability=min_probability,
        recommendations_only=recommendations_only,
        limit=limit,
        storefront_policy=storefront_policy,
    )
    effective_filters = filter_ctx["effective"]

    prepared_events = _prepare_output_events(
        events=localized_events,
        sport_filter=sport,
        min_quality=effective_filters["min_quality"],
        min_probability=effective_filters["min_probability"],
        recommendations_only=effective_filters["recommendations_only"],
        sort_by=effective_filters["sort_by"],
        limit=effective_filters["limit"],
    )

    top_recommendations = []
    if include_top:
        top_recommendations = _collect_top_recommendations(
            prepared_events,
            limit=min(max(1, _safe_int(top_limit, 10)), max(1, _safe_int(effective_filters["limit"], 10))),
            min_probability=effective_filters["min_probability"],
        )

    return {
        "total": len(prepared_events),
        "total_before_filters": len(localized_events),
        "language": selected_lang,
        "filters": {
            "sport": sport,
            **filter_ctx,
        },
        "storefront_policy": storefront_policy,
        "storefront_policy_context": {
            "policy_mode_requested": storefront_context.get("policy_mode_requested", "auto"),
            "adaptive_policy_enabled": storefront_context.get("adaptive_policy_enabled", True),
            "base_policy_mode": (storefront_context.get("base_policy") or {}).get("mode"),
        },
        "meta": _build_events_meta(prepared_events, len(localized_events)),
        "events": prepared_events,
        "top_recommendations": top_recommendations,
    }


@app.get("/api/events/{sport}")
async def get_events_by_sport(
    sport: str,
    lang: str = "ru",
    min_probability: float = 0.0,
    sort_by: str = "priority",
    limit: int = 30,
    policy_mode: str = "auto",
    adaptive_policy: bool = True,
):
    """Получить события по виду спорта."""
    selected_lang = _normalize_lang(lang)
    events = await _get_runtime_events()
    localized_events = _localize_events(events, selected_lang)

    storefront_context = _build_storefront_context(policy_mode=policy_mode, adaptive_policy_enabled=adaptive_policy)
    storefront_policy = storefront_context.get("policy", {})
    filter_ctx = _resolve_storefront_effective_filters(
        sort_by=sort_by,
        min_quality=0.0,
        min_probability=min_probability,
        recommendations_only=False,
        limit=limit,
        storefront_policy=storefront_policy,
    )
    effective_filters = filter_ctx["effective"]

    prepared_events = _prepare_output_events(
        events=localized_events,
        sport_filter=sport,
        min_quality=effective_filters["min_quality"],
        min_probability=effective_filters["min_probability"],
        recommendations_only=effective_filters["recommendations_only"],
        sort_by=effective_filters["sort_by"],
        limit=effective_filters["limit"],
    )

    return {
        "sport": sport,
        "language": selected_lang,
        "total": len(prepared_events),
        "filters": filter_ctx,
        "storefront_policy": storefront_policy,
        "storefront_policy_context": {
            "policy_mode_requested": storefront_context.get("policy_mode_requested", "auto"),
            "adaptive_policy_enabled": storefront_context.get("adaptive_policy_enabled", True),
            "base_policy_mode": (storefront_context.get("base_policy") or {}).get("mode"),
        },
        "meta": _build_events_meta(prepared_events, len(localized_events)),
        "events": prepared_events,
        "top_recommendations": _collect_top_recommendations(
            prepared_events,
            limit=min(10, max(1, _safe_int(effective_filters["limit"], 10))),
            min_probability=effective_filters["min_probability"],
        ),
    }


@app.get("/api/recommendations/top")
async def get_top_recommendations(
    lang: str = "ru",
    sport: Optional[str] = None,
    limit: int = 10,
    min_probability: float = 0.0,
    policy_mode: str = "auto",
    adaptive_policy: bool = True,
):
    """Плоский список лучших рекомендаций для витрины."""
    selected_lang = _normalize_lang(lang)
    events = await _get_runtime_events()
    localized_events = _localize_events(events, selected_lang)

    storefront_context = _build_storefront_context(policy_mode=policy_mode, adaptive_policy_enabled=adaptive_policy)
    storefront_policy = storefront_context.get("policy", {})
    filter_ctx = _resolve_storefront_effective_filters(
        sort_by="priority",
        min_quality=0.0,
        min_probability=min_probability,
        recommendations_only=True,
        limit=200,
        storefront_policy=storefront_policy,
    )
    effective_filters = filter_ctx["effective"]

    prepared_events = _prepare_output_events(
        events=localized_events,
        sport_filter=sport,
        min_quality=effective_filters["min_quality"],
        min_probability=effective_filters["min_probability"],
        recommendations_only=effective_filters["recommendations_only"],
        sort_by=effective_filters["sort_by"],
        limit=effective_filters["limit"],
    )

    recommendations = _collect_top_recommendations(
        prepared_events,
        limit=min(max(1, _safe_int(limit, 10)), max(1, _safe_int(effective_filters["limit"], 10))),
        min_probability=effective_filters["min_probability"],
    )

    return {
        "language": selected_lang,
        "sport": sport,
        "total": len(recommendations),
        "filters": filter_ctx,
        "storefront_policy": storefront_policy,
        "storefront_policy_context": {
            "policy_mode_requested": storefront_context.get("policy_mode_requested", "auto"),
            "adaptive_policy_enabled": storefront_context.get("adaptive_policy_enabled", True),
            "base_policy_mode": (storefront_context.get("base_policy") or {}).get("mode"),
        },
        "recommendations": recommendations,
    }


@app.get("/api/sports")
async def get_sports_list(lang: str = "ru"):
    """Получить список видов спорта"""
    selected_lang = _normalize_lang(lang)
    events = await _get_runtime_events()
    sports: Dict[str, Dict[str, Any]] = {}

    for event in events:
        sport_code = str(event.get("sport", "other")).lower()
        labels = _get_sport_labels(sport_code)
        if sport_code not in sports:
            sports[sport_code] = {
                "code": sport_code,
                "ru": labels["ru"],
                "en": labels["en"],
                "label": labels["ru"] if selected_lang == "ru" else labels["en"],
                "count": 0,
            }
        sports[sport_code]["count"] += 1

    return {
        "language": selected_lang,
        "sports": sports,
        "total_events": len(events),
    }


@app.get("/api/source-status")
async def source_status(refresh: bool = False):
    """Диагностика источника данных: real API или fallback."""
    if refresh:
        await _get_runtime_events(force_refresh=True)

    now_ts = asyncio.get_running_loop().time()
    cache_ts = float(RUNTIME_EVENTS_CACHE.get("ts", 0.0))
    cache_age_seconds = None if cache_ts <= 0 else round(max(0.0, now_ts - cache_ts), 2)

    cached_events = RUNTIME_EVENTS_CACHE.get("events") or []
    if not isinstance(cached_events, list):
        cached_events = []

    learning_status = _get_self_learning_status()

    return {
        "api_key_present": bool(_resolve_odds_api_key()),
        "supported_languages": ["ru", "en"],
        "cache_ttl_seconds": REAL_EVENTS_CACHE_TTL_SECONDS,
        "cache_age_seconds": cache_age_seconds,
        "cached_events_count": len(cached_events),
        "cache_source": RUNTIME_EVENTS_CACHE.get("source", "unknown"),
        "source_status": REAL_SOURCE_STATUS,
        "quality_filters": {
            "supported_runtime_sports": sorted(SUPPORTED_RUNTIME_SPORTS),
            "min_bookmakers_per_event": MIN_BOOKMAKERS_PER_EVENT,
            "min_recommendation_probability": MIN_RECOMMENDATION_PROBABILITY,
            "min_recommendation_coefficient": MIN_RECOMMENDATION_COEFFICIENT,
            "min_recommendation_edge": MIN_RECOMMENDATION_EDGE,
            "max_lines_per_market": MAX_LINES_PER_MARKET,
            "effective_min_recommendation_probability": REAL_SOURCE_STATUS.get("adaptive_min_probability") or MIN_RECOMMENDATION_PROBABILITY,
            "adaptive_threshold_enabled": ADAPTIVE_THRESHOLD_ENABLED,
            "adaptive_threshold_min_feedback": ADAPTIVE_THRESHOLD_MIN_FEEDBACK,
            "adaptive_min_probability_floor": ADAPTIVE_MIN_PROBABILITY_FLOOR,
            "adaptive_min_probability_ceil": ADAPTIVE_MIN_PROBABILITY_CEIL,
            "min_event_quality_score": MIN_EVENT_QUALITY_SCORE,
            "max_recommendations_per_event": MAX_RECOMMENDATIONS_PER_EVENT,
            "max_upcoming_hours": REAL_EVENTS_MAX_UPCOMING_HOURS,
        },
        "self_learning": {
            "enabled": SELF_LEARNING_ENABLED,
            "total_feedback": learning_status.get("total_feedback", 0),
            "sports_with_feedback": len(learning_status.get("sports", {})),
            "summary": learning_status.get("summary", {}),
        },
        "storefront_policy": _build_storefront_context(status=learning_status, policy_mode="auto", adaptive_policy_enabled=True).get("policy", {}),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


@app.get("/api/learning/status")
async def get_learning_status():
    """Статус самообучения по видам спорта."""
    return _get_self_learning_status()


@app.get("/api/learning/metrics")
async def get_learning_metrics(
    recent_limit: int = 20,
    recent_window_hours: int = 24,
    baseline_window_hours: int = 168,
    alert_min_samples: int = 10,
    policy_mode: str = "auto",
    adaptive_policy: bool = True,
):
    """Расширенные метрики самообучения (калибровка, Brier, ROI, recent feedback, тренды, алерты)."""
    status = _get_self_learning_status()
    full_recent_feedback = _get_recent_feedback(limit=SELF_LEARNING_HISTORY_LIMIT)
    windows = _compute_learning_windows(
        recent_feedback=full_recent_feedback,
        recent_window_hours=recent_window_hours,
        baseline_window_hours=baseline_window_hours,
    )
    alerts = _build_learning_alerts(windows, min_samples=alert_min_samples)

    threshold_guidance = _compute_adaptive_min_probability(status)
    storefront_context = _build_storefront_context(
        status=status,
        policy_mode=policy_mode,
        adaptive_policy_enabled=adaptive_policy,
    )

    return {
        "status": status,
        "quality_threshold": threshold_guidance,
        "storefront_policy": storefront_context.get("policy", {}),
        "storefront_policy_context": {
            "policy_mode_requested": storefront_context.get("policy_mode_requested", "auto"),
            "adaptive_policy_enabled": storefront_context.get("adaptive_policy_enabled", True),
            "base_policy_mode": (storefront_context.get("base_policy") or {}).get("mode"),
        },
        "windows": windows,
        "alerts": alerts,
        "recent_feedback": _get_recent_feedback(limit=recent_limit),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


@app.post("/api/learning/feedback")
async def post_learning_feedback(request: Request = None):
    """Принять результат прогноза и обновить self-learning статистику.

    Ожидаемый payload:
    {
      "sport": "football",
      "predicted_probability": 0.63,
      "outcome": true
    }
    """
    if not SELF_LEARNING_ENABLED:
        raise HTTPException(status_code=400, detail="self_learning_disabled")

    payload = await _read_json_payload(request)
    sport_code = _normalize_sport_key(
        str(payload.get("sport") or payload.get("sport_code") or "other")
    )

    outcome = _parse_outcome(payload.get("outcome"))
    if outcome is None:
        raise HTTPException(status_code=400, detail="invalid_outcome")

    probability_raw = payload.get("predicted_probability", payload.get("probability"))
    try:
        predicted_probability = float(probability_raw)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="invalid_probability")

    coefficient: Optional[float] = None
    coefficient_raw = payload.get("coefficient")
    if coefficient_raw is not None:
        try:
            coefficient = float(coefficient_raw)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="invalid_coefficient")

    metadata = {
        "event_id": payload.get("event_id"),
        "line": payload.get("line"),
        "source": payload.get("source"),
    }

    updated = _record_learning_feedback(
        sport_code=sport_code,
        predicted_probability=predicted_probability,
        outcome=outcome,
        coefficient=coefficient,
        metadata=metadata,
    )
    return {
        "ok": True,
        "sport": sport_code,
        "learning": updated,
        "summary": _get_self_learning_status().get("summary", {}),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


@app.get("/api/debug")
async def debug_info():
    """Полная диагностика системы"""
    events = await _get_runtime_events()
    return {
        "version": "12.0",
        "total_live_events": len(events),
        "sample_events": events[:3],
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


async def _read_json_payload(request: Request = None) -> Dict[str, Any]:
    """Безопасно прочитать JSON body запроса."""
    if request is None:
        return {}

    try:
        payload = await request.json()
        if isinstance(payload, dict):
            return payload
    except Exception:
        # Пустой body или невалидный JSON — не ошибка, просто берём значения по умолчанию.
        pass

    return {}


def _build_state_response(payload: Dict[str, Any], events: List[Dict[str, Any]], lang: str = "ru") -> Dict[str, Any]:
    """Построить ответ в формате single-event."""
    if not events:
        logger.warning("⚠️ Нет live событий")
        return {
            "match_info": {"league": "—", "home": "—", "away": "—", "status": "—", "sport": "—"},
            "recommendations": [],
            "event_index": 0,
            "total_events": 0,
        }

    raw_index = payload.get("event_index", 0)
    try:
        event_index = int(raw_index)
    except (TypeError, ValueError):
        event_index = 0

    event_index = event_index % len(events)
    event = events[event_index]
    selected_lang = _normalize_lang(lang)
    localized_event = _localize_event(event, selected_lang)

    recommendations = []
    for rec in localized_event.get("recommendations", []):
        recommendations.append({
            "league": localized_event.get("league", "—"),
            "sport": rec.get("sport", localized_event.get("sport", "—")),
            "sport_code": rec.get("sport_code", localized_event.get("sport_code", "other")),
            "sport_ru": rec.get("sport_ru", "Спорт"),
            "sport_en": rec.get("sport_en", "Sport"),
            "home": localized_event.get("home", "—"),
            "away": localized_event.get("away", "—"),
            "line": rec.get("line", "Исход"),
            "confidence": rec.get("confidence", "med"),
            "probability": rec.get("probability", 0),
            "coefficient": rec.get("coefficient", 1.5),
        })

    logger.info(
        f"✅ Возвращаю {len(recommendations)} рекомендаций для "
        f"{event['home']} vs {event['away']} (index={event_index})"
    )

    return {
        "language": selected_lang,
        "match_info": {
            "league": localized_event.get("league", "—"),
            "home": localized_event.get("home", "—"),
            "away": localized_event.get("away", "—"),
            "status": f"{event.get('time', '—')} ({event.get('score', '—')})",
            "sport": localized_event.get("sport", "—"),
            "sport_code": localized_event.get("sport_code", "other"),
            "sport_ru": localized_event.get("sport_ru", "Спорт"),
            "sport_en": localized_event.get("sport_en", "Sport"),
        },
        "recommendations": recommendations,
        "event_index": event_index,
        "total_events": len(events),
    }


if __name__ == "__main__":
    import uvicorn
    target_port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=target_port)
