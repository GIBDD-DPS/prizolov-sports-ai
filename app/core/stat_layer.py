# ============================================
# Prizolov Sports AI - Setup
# Version: 4.01 (Social Sentiment & Global AI Upgrade)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at prizolov.ru
# ============================================

import math
import structlog
from typing import Dict, Any

log = structlog.get_logger()

def _poisson_probability(lambda_val: float, k: int) -> float:
    """Вычисление вероятности k событий при среднем lambda_val (распределение Пуассона)"""
    if lambda_val <= 0:
        return 0.0
    return (math.exp(-lambda_val) * (lambda_val ** k)) / math.factorial(k)

async def calculate_stat_probabilities(match_data: Dict[str, Any]) -> Dict[str, float]:
    """
    Статистический слой прогноза.
    Базовый расчёт через распределение Пуассона с корректировкой на ожидаемые голы (xG),
    домашнее преимущество и коэффициентную маржу.
    В будущем значения expected_home/away_goals будут подтягиваться из исторической БД.
    """
    match_id = match_data.get("match_id", "unknown")
    log.debug("Stat layer: calculating baseline probabilities", match_id=match_id)

    odds = match_data.get("odds", {})
    home_odds = float(odds.get("1", 2.0) or 2.0)
    draw_odds = float(odds.get("X", 3.5) or 3.5)
    away_odds = float(odds.get("2", 2.0) or 2.0)

    # Эвристическая оценка ожидаемых голов (xG) на основе букмекерской линии
    # В продакшене заменяется на запрос к БД: SELECT avg_xg_home, avg_xg_away WHERE ...
    base_xg_home = 1.35
    base_xg_away = 1.10
    
    # Корректировка xG на силу коэффициентов (ниже кэф -> выше ожидаемая результативность)
    xg_home = base_xg_home * (2.0 / home_odds)
    xg_away = base_xg_away * (2.0 / away_odds)

    # Домашнее преимущество (+12% к вероятности забитого гола)
    xg_home *= 1.12

    # Расчёт матрицы вероятностей через Пуассон (до 6 голов включительно)
    max_goals = 7
    home_goal_probs = [_poisson_probability(xg_home, i) for i in range(max_goals)]
    away_goal_probs = [_poisson_probability(xg_away, i) for i in range(max_goals)]

    prob_home_win = 0.0
    prob_draw = 0.0
    prob_away_win = 0.0

    for h in range(max_goals):
        for a in range(max_goals):
            joint_prob = home_goal_probs[h] * away_goal_probs[a]
            if h > a:
                prob_home_win += joint_prob
            elif h == a:
                prob_draw += joint_prob
            else:
                prob_away_win += joint_prob

    # Нормализация (сумма вероятностей должна быть строго 1.0)
    total = prob_home_win + prob_draw + prob_away_win
    if total <= 0:
        total = 1.0

    final_probs = {
        "home_win": round(prob_home_win / total, 4),
        "draw": round(prob_draw / total, 4),
        "away_win": round(prob_away_win / total, 4)
    }

    log.info("Stat layer complete", match_id=match_id, probs=final_probs)
    return final_probs
