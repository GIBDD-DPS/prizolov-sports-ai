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
SELF_LEARNING_STATE: Dict[str, Any] = {
    "updated_at": None,
    "total_feedback": 0,
    "sports": {},
}
SELF_LEARNING_LOCK = Lock()


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

        rec_local["sport_code"] = sport_code
        rec_local["sport_ru"] = labels["ru"]
        rec_local["sport_en"] = labels["en"]
        rec_local["sport"] = labels["ru"] if lang == "ru" else labels["en"]
        rec_local["base_probability"] = round(base_probability, 4)
        rec_local["probability"] = round(adjusted_probability, 4)
        rec_local["learning_factor"] = learning_meta["factor"]
        rec_local["learning_feedback_count"] = learning_meta["feedback_count"]
        rec_local["confidence"] = _probability_to_confidence(adjusted_probability)
        recs.append(rec_local)

    localized["recommendations"] = recs
    return localized


def _localize_events(events: List[Dict[str, Any]], lang: str) -> List[Dict[str, Any]]:
    selected_lang = _normalize_lang(lang)
    return [_localize_event(event, selected_lang) for event in events]


def _default_learning_sport_state() -> Dict[str, Any]:
    return {
        "feedback_count": 0,
        "hits": 0,
        "sum_predicted_probability": 0.0,
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
                "last_updated": stats.get("last_updated"),
            }

    with SELF_LEARNING_LOCK:
        SELF_LEARNING_STATE["updated_at"] = payload.get("updated_at")
        SELF_LEARNING_STATE["total_feedback"] = max(0, _safe_int(payload.get("total_feedback"), 0))
        SELF_LEARNING_STATE["sports"] = normalized_sports


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

    factor = _compute_learning_factor_from_stats(stats)
    avg_pred = round(sum_pred / feedback_count, 4) if feedback_count else None
    hit_rate = round(hits / feedback_count, 4) if feedback_count else None

    return {
        "sport_code": normalized_sport,
        "factor": factor,
        "feedback_count": feedback_count,
        "hits": hits,
        "avg_predicted_probability": avg_pred,
        "hit_rate": hit_rate,
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


def _record_learning_feedback(sport_code: str, predicted_probability: float, outcome: bool) -> Dict[str, Any]:
    normalized_sport = _normalize_sport_key(sport_code)
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    probability = _normalize_probability(predicted_probability)

    with SELF_LEARNING_LOCK:
        stats = _ensure_learning_stats_locked(normalized_sport)
        stats["feedback_count"] = max(0, _safe_int(stats.get("feedback_count"), 0)) + 1
        stats["hits"] = max(0, _safe_int(stats.get("hits"), 0)) + (1 if outcome else 0)
        stats["sum_predicted_probability"] = max(0.0, _safe_float(stats.get("sum_predicted_probability"), 0.0)) + probability
        stats["last_updated"] = now_iso

        SELF_LEARNING_STATE["total_feedback"] = max(0, _safe_int(SELF_LEARNING_STATE.get("total_feedback"), 0)) + 1
        SELF_LEARNING_STATE["updated_at"] = now_iso

        _save_self_learning_state_locked()

    return _get_learning_meta(normalized_sport)


def _get_self_learning_status() -> Dict[str, Any]:
    with SELF_LEARNING_LOCK:
        total_feedback = max(0, _safe_int(SELF_LEARNING_STATE.get("total_feedback"), 0))
        updated_at = SELF_LEARNING_STATE.get("updated_at")
        sports_keys = sorted((SELF_LEARNING_STATE.get("sports") or {}).keys())

    sports: Dict[str, Any] = {}
    for sport_code in sports_keys:
        sports[sport_code] = _get_learning_meta(sport_code)

    return {
        "enabled": SELF_LEARNING_ENABLED,
        "min_feedback": SELF_LEARNING_MIN_FEEDBACK,
        "max_factor_shift": SELF_LEARNING_MAX_FACTOR_SHIFT,
        "state_path": SELF_LEARNING_STATE_PATH,
        "total_feedback": total_feedback,
        "updated_at": updated_at,
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


def _extract_recommendations(event: Dict[str, Any], league: str, sport: str, home: str, away: str) -> List[Dict[str, Any]]:
    recommendations: List[Dict[str, Any]] = []
    bookmakers = event.get("bookmakers") or []

    if not isinstance(bookmakers, list):
        return recommendations

    chosen_market: Optional[Dict[str, Any]] = None
    for bookmaker in bookmakers:
        for market in bookmaker.get("markets") or []:
            if market.get("key") in {"h2h", "totals", "spreads"}:
                chosen_market = market
                break
        if chosen_market:
            break

    if not chosen_market:
        return recommendations

    outcomes = chosen_market.get("outcomes") or []
    if not isinstance(outcomes, list):
        return recommendations

    probabilities = _compute_probabilities(outcomes)
    market_key = chosen_market.get("key", "h2h")

    for outcome in outcomes[:3]:
        try:
            price = float(outcome.get("price"))
        except (TypeError, ValueError):
            continue

        if price <= 1.0:
            continue

        line_name = str(outcome.get("name") or "Исход")
        point = outcome.get("point")
        if point is not None:
            line_name = f"{line_name} {point}"

        probability = probabilities.get(str(outcome.get("name") or "Исход"), round(min(0.99, 1.0 / price), 4))

        recommendations.append(
            {
                "league": league,
                "sport": sport,
                "home": home,
                "away": away,
                "line": line_name if market_key != "h2h" else f"{market_key.upper()}: {line_name}",
                "confidence": "high" if probability >= 0.45 else "med",
                "probability": probability,
                "coefficient": round(price, 2),
            }
        )

    return recommendations


def _transform_odds_event(event: Dict[str, Any], now_utc: datetime.datetime) -> Optional[Dict[str, Any]]:
    home = event.get("home_team")
    away = event.get("away_team")
    if not home or not away:
        return None

    sport = _normalize_sport_key(event.get("sport_key"))
    league = event.get("sport_title") or event.get("sport_key") or "Unknown League"
    commence_time = event.get("commence_time")
    commence_dt = _parse_iso_datetime(commence_time)

    status = "UPCOMING"
    if commence_dt and commence_dt <= now_utc:
        status = "LIVE"

    recommendations = _extract_recommendations(event, league, sport, home, away)

    return {
        "id": event.get("id") or f"{sport}_{home}_{away}",
        "sport": sport,
        "league": league,
        "home": home,
        "away": away,
        "status": status,
        "time": "LIVE" if status == "LIVE" else _format_event_time(commence_time),
        "score": "—",
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

    for item in payload:
        if not isinstance(item, dict):
            continue
        transformed = _transform_odds_event(item, now_utc)
        if transformed:
            events.append(transformed)

    events.sort(key=lambda ev: (ev.get("status") != "LIVE", ev.get("time", "")))
    result = events[:limit]

    REAL_SOURCE_STATUS["last_fetch_ok"] = True
    REAL_SOURCE_STATUS["last_http_status"] = 200
    REAL_SOURCE_STATUS["last_error"] = None
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
async def get_all_events(lang: str = "ru"):
    """Получить все live события"""
    selected_lang = _normalize_lang(lang)
    events = await _get_runtime_events()
    localized_events = _localize_events(events, selected_lang)
    return {
        "total": len(localized_events),
        "language": selected_lang,
        "events": localized_events,
    }


@app.get("/api/events/{sport}")
async def get_events_by_sport(sport: str, lang: str = "ru"):
    """Получить события по виду спорта"""
    selected_lang = _normalize_lang(lang)
    events = await _get_runtime_events()
    matches = get_matches_by_sport(sport.lower(), events)
    localized_matches = _localize_events(matches, selected_lang)
    return {
        "sport": sport,
        "language": selected_lang,
        "total": len(localized_matches),
        "events": localized_matches,
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
        "self_learning": {
            "enabled": SELF_LEARNING_ENABLED,
            "total_feedback": learning_status.get("total_feedback", 0),
            "sports_with_feedback": len(learning_status.get("sports", {})),
        },
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


@app.get("/api/learning/status")
async def get_learning_status():
    """Статус самообучения по видам спорта."""
    return _get_self_learning_status()


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

    updated = _record_learning_feedback(sport_code, predicted_probability, outcome)
    return {
        "ok": True,
        "sport": sport_code,
        "learning": updated,
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
