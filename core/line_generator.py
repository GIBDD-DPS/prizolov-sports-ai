# ============================================
# Prizolov Sports AI - Core Broad Line Generator
# Version: 3.01 (Initial Architecture Release)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at prizolov.ru
# ============================================

import math
from typing import Dict, Any, List

class BroadLineGenerator:
    """Математический движок для расчета динамических коэффициентов спортивной линии"""

    def __init__(self, default_margin: float = 1.05):
        """
        Args:
            default_margin: Коэффициент маржи букмекера (1.05 = 5% маржи)
        """
        self.margin = default_margin

    def _poisson_probability(self, k: int, lmbda: float) -> float:
        """Расчет вероятности наступления ровно k событий при интенсивности lmbda"""
        if lmbda <= 0:
            return 1.0 if k == 0 else 0.0
        try:
            return (lmbda ** k * math.exp(-lmbda)) / math.factorial(k)
        except OverflowError:
            return 0.0

    def calculate_poisson_line(self, 
                               lambda_team_a: float, 
                               lambda_team_b: float, 
                               time_left_ratio: float, 
                               current_score_a: int, 
                               current_score_b: int,
                               max_goals_to_simulate: int = 15) -> Dict[str, List[Dict[str, Any]]]:
        """
        Генерирует базовые рынки (1Х2, Тоталы матча) на основе Пуассоновского распределения.
        Подходит для футбола и хоккея.
        """
        # Корректируем ожидаемую интенсивность на оставшееся игровое время
        rem_lambda_a = max(lambda_team_a * time_left_ratio, 0.01)
        rem_lambda_b = max(lambda_team_b * time_left_ratio, 0.01)

        # Матрица вероятностей точных счетов оставшегося времени
        prob_matrix = {}
        for i in range(max_goals_to_simulate):
            p_a = self._poisson_probability(i, rem_lambda_a)
            for j in range(max_goals_to_simulate):
                p_b = self._poisson_probability(j, rem_lambda_b)
                prob_matrix[(i, j)] = p_a * p_b

        # Агрегация вероятностей финальных исходов (с учетом текущего счета)
        p_win_a = 0.0
        p_draw = 0.0
        p_win_b = 0.0
        
        # Расчет тоталов (карта вероятностей для суммарного тотала)
        total_probs = {}

        for (rem_a, rem_b), p in prob_matrix.items():
            final_a = current_score_a + rem_a
            final_b = current_score_b + rem_b
            total_goals = final_a + final_b

            # 1Х2
            if final_a > final_b:
                p_win_a += p
            elif final_a == final_b:
                p_draw += p
            else:
                p_win_b += p

            # Тоталы
            total_probs[total_goals] = total_probs.get(total_goals, 0.0) + p

        # Формирование рынка 1Х2
        p_win_a = max(p_win_a, 0.001)
        p_draw = max(p_draw, 0.001)
        p_win_b = max(p_win_b, 0.001)

        main_outcomes = [
            {"market_name": "1", "odds": round((1.0 / p_win_a) * self.margin, 2), "is_suspended": False},
            {"market_name": "X", "odds": round((1.0 / p_draw) * self.margin, 2), "is_suspended": False},
            {"market_name": "2", "odds": round((1.0 / p_win_b) * self.margin, 2), "is_suspended": False}
        ]

        # Формирование линейки Тоталов (основные коридоры вокруг текущего значения)
        totals = []
        current_total_base = current_score_a + current_score_b
        
        # Генерируем 3 базовых тотала: базовый текущий, +1.5, +2.5
        for t_offset in [0.5, 1.5, 2.5]:
            target_total = current_total_base + t_offset
            
            # Вероятность ТМ (Тотал Меньше)
            p_under = sum(p for tg, p in total_probs.items() if tg < target_total)
            p_under = max(min(p_under, 0.999), 0.001)
            p_over = 1.0 - p_under
            p_over = max(min(p_over, 0.999), 0.001)

            totals.append({"market_name": f"TO {target_total}", "odds": round((1.0 / p_over) * self.margin, 2), "is_suspended": False})
            totals.append({"market_name": f"TU {target_total}", "odds": round((1.0 / p_under) * self.margin, 2), "is_suspended": False})

        return {
            "main_outcomes": main_outcomes,
            "totals": totals,
            "handicaps": [] # Заполняется точечно в зависимости от специфики спорта
        }

    def calculate_high_score_line(self, 
                                  pace: float, 
                                  efficiency_a: float, 
                                  efficiency_b: float, 
                                  time_left_ratio: float, 
                                  current_score_a: int, 
                                  current_score_b: int) -> Dict[str, List[Dict[str, Any]]]:
        """
        Генерирует рынки для высокорезультативных видов спорта (Баскетбол).
        Использует нормальную аппроксимацию.
        """
        # Расчет ожидаемых очков за оставшееся время
        possessions_left = pace * time_left_ratio
        exp_rem_a = (possessions_left / 2) * efficiency_a
        exp_rem_b = (possessions_left / 2) * efficiency_b

        proj_final_a = current_score_a + exp_rem_a
        proj_final_b = current_score_b + exp_rem_b
        
        # Дисперсия (среднее отклонение) для баскетбольных матчей
        variance = 12.0 
        
        # Расчет базового исхода 1-2 (без ничьих в баскетболе)
        diff = proj_final_a - proj_final_b
        
        # Использование функции ошибок для аппроксимации интеграла нормального распределения
        p_win_a = 0.5 * (1 + math.erf(diff / (variance * math.sqrt(2))))
        p_win_a = max(min(p_win_a, 0.999), 0.001)
        p_win_b = 1.0 - p_win_a

        main_outcomes = [
            {"market_name": "1", "odds": round((1.0 / p_win_a) * self.margin, 2), "is_suspended": False},
            {"market_name": "2", "odds": round((1.0 / p_win_b) * self.margin, 2), "is_suspended": False}
        ]

        # Базовый тотал матча
        proj_total = proj_final_a + proj_final_b
        totals = []
        
        # Шаг тотала для баскетбола
        base_total = round(proj_total * 2) / 2 # Округление до 0.5 пункта
        
        for offset in [-5.5, 0.0, 5.5]:
            target_total = base_total + offset
            # Вероятность того, что финальный тотал будет меньше целевого
            z_score = (target_total - proj_total) / variance
            p_under = 0.5 * (1 + math.erf(z_score / math.sqrt(2)))
            p_under = max(min(p_under, 0.999), 0.001)
            p_over = 1.0 - p_under

            totals.append({"market_name": f"TO {target_total}", "odds": round((1.0 / p_over) * self.margin, 2), "is_suspended": False})
            totals.append({"market_name": f"TU {target_total}", "odds": round((1.0 / p_under) * self.margin, 2), "is_suspended": False})

        return {
            "main_outcomes": main_outcomes,
            "totals": totals,
            "handicaps": []
        }
