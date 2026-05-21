# ============================================
# Prizolov Sports AI - Football Analytics Module
# Version: 1.00 (+1.00: Real-time Poisson/xG Modeling & Live Probability Engine)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at cloud.amvera.ru
# ============================================

import numpy as np
from scipy.stats import poisson
from datetime import datetime
import json
from typing import Dict, Any, Optional


class FootballAnalyzer:
    def __init__(self):
        self.home_advantage = 1.12
        self.draw_factor = 1.25
        self.max_goals = 8

    def calculate_xg_and_probs(self, 
                               team_a_strength: float, 
                               team_b_strength: float,
                               minute: int = 45,
                               is_home_team_a: bool = True) -> Dict[str, Any]:
        """
        Основная функция расчёта xG и вероятностей
        """
        # Базовые expected goals
        lambda_a = (team_a_strength / 100) * 1.38
        lambda_b = (team_b_strength / 100) * 1.32

        if is_home_team_a:
            lambda_a *= self.home_advantage
        else:
            lambda_b *= self.home_advantage

        # Корректировка по времени матча (усталость, давление)
        time_factor = 1 + (minute - 45) * 0.003
        lambda_a = max(0.3, lambda_a * time_factor)
        lambda_b = max(0.3, lambda_b * time_factor)

        # Построение матрицы вероятностей
        probs = np.zeros((self.max_goals, self.max_goals))
        
        for i in range(self.max_goals):
            for j in range(self.max_goals):
                probs[i, j] = poisson.pmf(i, lambda_a) * poisson.pmf(j, lambda_b)

        # Dixon-Coles корректировка (увеличивает вероятность низовых ничьих)
        rho = 0.025
        for i in range(0, 4):
            for j in range(0, 4):
                if i == j == 0:
                    probs[i, j] *= (1 + rho * 1.5)
                elif i == j:
                    probs[i, j] *= (1 + rho)

        # Нормализация
        probs_sum = probs.sum()
        if probs_sum > 0:
            probs /= probs_sum

        # Агрегация исходов
        home_win_prob = np.sum(np.tril(probs, -1))      # Team A > Team B
        away_win_prob = np.sum(np.triu(probs, 1))       # Team A < Team B
        draw_prob = np.sum(np.diag(probs))

        # Самый вероятный счёт
        most_likely = np.unravel_index(probs.argmax(), probs.shape)

        result = {
            "team_a_xg": round(float(lambda_a), 2),
            "team_b_xg": round(float(lambda_b), 2),
            "probabilities": {
                "Team A win": round(float(home_win_prob) * 100, 1),
                "Team B win": round(float(away_win_prob) * 100, 1),
                "Draw": round(float(draw_prob) * 100, 1)
            },
            "most_likely_score": f"{most_likely[0]}:{most_likely[1]}",
            "confidence": round(float(max(home_win_prob, away_win_prob, draw_prob)) * 100, 1),
            "total_xg": round(float(lambda_a + lambda_b), 2),
            "timestamp": datetime.utcnow().isoformat()
        }

        # Добавляем рекомендации
        result["recommendations"] = self._generate_recommendations(result)
        
        return result

    def _generate_recommendations(self, data: Dict) -> list:
        """Генерация AI-рекомендаций"""
        recs = []
        probs = data["probabilities"]
        total_xg = data["total_xg"]

        # Тотал больше/меньше 2.5
        over_25_prob = 1 - sum(poisson.cdf(2, data["team_a_xg"]) * poisson.pmf(k, data["team_b_xg"]) 
                             for k in range(3))

        if over_25_prob > 0.58:
            recs.append({
                "market": "Total Over 2.5",
                "probability": round(over_25_prob * 100, 1),
                "value": round(over_25_prob - 0.52, 2),   # пример value
                "confidence": "High" if over_25_prob > 0.65 else "Medium"
            })

        # Основные исходы
        best_outcome = max(probs.items(), key=lambda x: x[1])
        if best_outcome[1] > 48:
            recs.append({
                "market": best_outcome[0],
                "probability": best_outcome[1],
                "value": 0.08,
                "confidence": "High"
            })

        return recs[:3]  # максимум 3 рекомендации

    def get_full_match_data(self, team_a_strength=120.0, team_b_strength=120.0, 
                           minute=45, match_id="demo_match") -> Dict:
        """Полные данные для WebSocket / дашборда"""
        analysis = self.calculate_xg_and_probs(
            team_a_strength, team_b_strength, minute
        )

        full_data = {
            "match_id": match_id,
            "sport": "football",
            "game_time": f"{minute}:00",
            "status": "live",
            "metrics": {
                "possession": {"Team A": 52, "Team B": 48},
                "dangerous_attacks": {"Team A": 14, "Team B": 11},
                "shots": {"Team A": 7, "Team B": 5},
            },
            "xg": {
                "team_a": analysis["team_a_xg"],
                "team_b": analysis["team_b_xg"],
                "total": analysis["total_xg"]
            },
            "line": analysis["probabilities"],
            "ai_recommendations": analysis["recommendations"],
            "most_likely_score": analysis["most_likely_score"],
            "confidence": analysis["confidence"],
            "timestamp": analysis["timestamp"]
        }

        return full_data


# Для быстрого тестирования
if __name__ == "__main__":
    analyzer = FootballAnalyzer()
    
    result = analyzer.get_full_match_data(
        team_a_strength=135.0,
        team_b_strength=108.0,
        minute=67
    )
    
    print(json.dumps(result, indent=2, ensure_ascii=False))
