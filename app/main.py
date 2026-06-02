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
MAX_RECOMMENDATIONS_PER_EVENT = max(1, int(os.environ.get("MAX_RECOMMENDATIONS_PER_EVENT", "3")))
REAL_EVENTS_MAX_UPCOMING_HOURS = max(1, int(os.environ.get("REAL_EVENTS_MAX_UPCOMING_HOURS", "72")))
MIN_EVENT_QUALITY_SCORE = min(100.0, max(0.0, float(os.environ.get("MIN_EVENT_QUALITY_SCORE", "42"))))


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
    if normalized in {"priority", "quality", "probability", "freshness", "time"}:
        return normalized
    return "priority"


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
    recommendations_factor = min(1.0, max(0.0, recommendations_count / max(1, MAX_RECOMMENDATIONS_PER_EVENT)))

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


def _extract_recommendations(event: Dict[str, Any], league: str, sport: str, home: str, away: str) -> List[Dict[str, Any]]:
    recommendations: List[Dict[str, Any]] = []
    bookmakers = event.get("bookmakers") or []

    if not isinstance(bookmakers, list) or len(bookmakers) < MIN_BOOKMAKERS_PER_EVENT:
        return recommendations

    market_candidates: List[Dict[str, Any]] = []
    for bookmaker in bookmakers:
        if not isinstance(bookmaker, dict):
            continue
        bookmaker_name = bookmaker.get("title") or bookmaker.get("key") or "bookmaker"
        for market in bookmaker.get("markets") or []:
            if not isinstance(market, dict):
                continue
            market_key = str(market.get("key") or "")
            if market_key not in {"h2h", "totals", "spreads"}:
                continue
            outcomes = market.get("outcomes") or []
            if isinstance(outcomes, list) and outcomes:
                market_candidates.append(
                    {
                        "market_key": market_key,
                        "outcomes": outcomes,
                        "bookmaker": bookmaker_name,
                    }
                )

    if not market_candidates:
        return recommendations

    market_priority = {"h2h": 0, "totals": 1, "spreads": 2}
    market_candidates.sort(
        key=lambda item: (
            market_priority.get(str(item.get("market_key")), 99),
            -len(item.get("outcomes") or []),
        )
    )
    chosen = market_candidates[0]
    outcomes = chosen.get("outcomes") or []
    market_key = str(chosen.get("market_key") or "h2h")

    probabilities = _compute_probabilities(outcomes)
    scored_candidates: List[Dict[str, Any]] = []

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
        probability = probabilities.get(outcome_name, round(min(0.99, 1.0 / price), 4))
        probability = max(0.01, min(0.99, probability))

        if probability < MIN_RECOMMENDATION_PROBABILITY:
            continue

        scored_candidates.append(
            {
                "league": league,
                "sport": sport,
                "home": home,
                "away": away,
                "line": _build_recommendation_line(market_key, outcome_name, outcome.get("point")),
                "confidence": _probability_to_confidence(probability),
                "probability": round(probability, 4),
                "coefficient": round(price, 2),
                "confidence_score": round(probability, 4),
                "market": market_key,
                "bookmaker": chosen.get("bookmaker"),
                "value_score": _recommendation_strength(probability, price),
            }
        )

    scored_candidates.sort(key=lambda item: (item.get("value_score", 0.0), item.get("probability", 0.0)), reverse=True)
    recommendations.extend(scored_candidates[:MAX_RECOMMENDATIONS_PER_EVENT])
    return recommendations


def _transform_odds_event(event: Dict[str, Any], now_utc: datetime.datetime) -> Optional[Dict[str, Any]]:
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

    recommendations = _extract_recommendations(event, league, sport, home, away)
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
    events: List[Dict[str, Any]] = []
    filtered_out = 0

    for item in payload:
        if not isinstance(item, dict):
            filtered_out += 1
            continue
        transformed = _transform_odds_event(item, now_utc)
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
):
    """Получить все live события с фильтрами и ранжированием."""
    selected_lang = _normalize_lang(lang)
    events = await _get_runtime_events()
    localized_events = _localize_events(events, selected_lang)
    prepared_events = _prepare_output_events(
        events=localized_events,
        sport_filter=sport,
        min_quality=min_quality,
        min_probability=min_probability,
        recommendations_only=recommendations_only,
        sort_by=sort_by,
        limit=limit,
    )

    top_recommendations = []
    if include_top:
        top_recommendations = _collect_top_recommendations(
            prepared_events,
            limit=top_limit,
            min_probability=min_probability,
        )

    return {
        "total": len(prepared_events),
        "total_before_filters": len(localized_events),
        "language": selected_lang,
        "filters": {
            "sport": sport,
            "min_quality": min_quality,
            "min_probability": min_probability,
            "sort_by": _normalize_sort_by(sort_by),
            "limit": limit,
            "recommendations_only": recommendations_only,
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
):
    """Получить события по виду спорта."""
    selected_lang = _normalize_lang(lang)
    events = await _get_runtime_events()
    localized_events = _localize_events(events, selected_lang)
    prepared_events = _prepare_output_events(
        events=localized_events,
        sport_filter=sport,
        min_quality=0.0,
        min_probability=min_probability,
        recommendations_only=False,
        sort_by=sort_by,
        limit=limit,
    )

    return {
        "sport": sport,
        "language": selected_lang,
        "total": len(prepared_events),
        "filters": {
            "min_probability": min_probability,
            "sort_by": _normalize_sort_by(sort_by),
            "limit": limit,
        },
        "meta": _build_events_meta(prepared_events, len(localized_events)),
        "events": prepared_events,
        "top_recommendations": _collect_top_recommendations(prepared_events, limit=10, min_probability=min_probability),
    }


@app.get("/api/recommendations/top")
async def get_top_recommendations(
    lang: str = "ru",
    sport: Optional[str] = None,
    limit: int = 10,
    min_probability: float = 0.0,
):
    """Плоский список лучших рекомендаций для витрины."""
    selected_lang = _normalize_lang(lang)
    events = await _get_runtime_events()
    localized_events = _localize_events(events, selected_lang)
    prepared_events = _prepare_output_events(
        events=localized_events,
        sport_filter=sport,
        min_quality=0.0,
        min_probability=min_probability,
        recommendations_only=True,
        sort_by="priority",
        limit=200,
    )

    recommendations = _collect_top_recommendations(
        prepared_events,
        limit=limit,
        min_probability=min_probability,
    )

    return {
        "language": selected_lang,
        "sport": sport,
        "total": len(recommendations),
        "filters": {
            "min_probability": min_probability,
            "limit": limit,
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
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


@app.get("/api/learning/status")
async def get_learning_status():
    """Статус самообучения по видам спорта."""
    return _get_self_learning_status()


@app.get("/api/learning/metrics")
async def get_learning_metrics(recent_limit: int = 20):
    """Расширенные метрики самообучения (калибровка, Brier, ROI, recent feedback)."""
    status = _get_self_learning_status()
    return {
        "status": status,
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
