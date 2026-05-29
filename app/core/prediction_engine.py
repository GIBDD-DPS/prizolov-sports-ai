# ============================================
# Prizolov Sports AI - Setup
# Version: 4.01 (Social Sentiment & Global AI Upgrade)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at prizolov.ru
# ============================================

import structlog
from typing import Dict, Any
from app.core.stat_layer import calculate_stat_probabilities
from app.core.ml_layer import predict_with_ml
from app.core.ai_sentiment_layer import analyze_sentiment

log = structlog.get_logger()

def _safe_float(val: Any) -> float:
    """Безопасное преобразование коэффициента в float"""
    if val is None:
        return 2.0  # Дефолт для расчёта EV, если коэффициент отсутствует
    try:
        return float(str(val).replace(",", "."))
    except (ValueError, TypeError):
        return 2.0

async def generate_prediction(match_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Гибридный прогнозный движок.
    Комбинирует 3 слоя: Статистика (40%) → ML (40%) → AI/Sentiment (20%).
    Возвращает структурированный объект для API и записи в БД.
    """
    match_id = match_data.get("match_id", "unknown")
    log.info("🧠 Generating hybrid prediction", match_id=match_id)

    # 1. Статистический слой (Пуассон/Elo/форма)
    stat_probs = await calculate_stat_probabilities(match_data)
    
    # 2. ML-слой (LightGBM/XGBoost на исторических данных + линиях)
    ml_probs = await predict_with_ml(match_data, stat_probs)
    
    # 3. AI/Sentiment слой (NLP новостей/Telegram/соцсетей)
    sentiment_bias = await analyze_sentiment(match_data)

    # === Fusion (Взвешенное объединение вероятностей) ===
    # Работаем с вероятностью победы хозяев как основным маркером
    home_stat = stat_probs.get("home_win", 0.33)
    home_ml = ml_probs.get("home_win", 0.33)
    home_sent = sentiment_bias.get("home_win", 0.33)

    final_home_prob = (home_stat * 0.40) + (home_ml * 0.40) + (home_sent * 0.20)
    # Ограничиваем диапазон [0.01, 0.99]
    final_home_prob = max(0.01, min(0.99, final_home_prob))

    # === Расчёт метрик ===
    odds_home = _safe_float(match_data.get("odds", {}).get("1"))
    ev = (final_home_prob * odds_home) - 1.0

    # Определение уверенности
    if final_home_prob > 0.70 and ev > 0.12:
        confidence = "High"
    elif final_home_prob > 0.55 and ev > 0.04:
        confidence = "Med"
    else:
        confidence = "Low"

    # Формирование прогноза и рекомендации
    if final_home_prob > 0.65:
        outcome = "П1 (Победа хозяев)"
        bet_rec = f"П1 @ {odds_home}"
    elif final_home_prob < 0.35:
        odds_away = _safe_float(match_data.get("odds", {}).get("2"))
        outcome = "П2 (Победа гостей)"
        bet_rec = f"П2 @ {odds_away}"
    else:
        odds_x = _safe_float(match_data.get("odds", {}).get("X"))
        outcome = "X (Ничья / Двойной шанс)"
        bet_rec = f"1X/2X @ {odds_x}"

    # === Итоговый объект (точно по ТЗ) ===
    return {
        "home_team": match_data.get("home_team"),
        "away_team": match_data.get("away_team"),
        "start_time": match_data.get("start_time"),
        "current_minute": match_data.get("current_minute"),
        "odds": match_data.get("odds", {}),
        "prediction_outcome": outcome,
        "probability": round(final_home_prob * 100, 2),
        "recommended_bet": bet_rec,
        "expected_value": round(ev, 3),
        "confidence": confidence,
        # Техническое поле для отладки слоёв (не выводится в фронтенд)
        "internal_layers": {
            "stat": stat_probs,
            "ml": ml_probs,
            "ai_sentiment": sentiment_bias
        }
    }
