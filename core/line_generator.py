# ============================================
# Prizolov Sports AI - Core Broad Line Generator
# Version: 3.02 (Handicap Analytics Core)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at prizolov.ru
# ============================================

import math
from typing import Dict, Any, List

class BroadLineGenerator:
    """Математический движок для расчета динамических коэффициентов спортивной линии (Исходы, Тоталы, Форы)"""

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
        Генерирует базовые рынки (1Х2, Тоталы, Форы) на основе Пуассоновского распределения.
        Подходит для футбола и хоккея.
        """
        rem_lambda_a = max(lambda_team_a * time_left_ratio, 0.01)
        rem_lambda_b = max(lambda_team_b * time_left_ratio, 0.01)

        # Матрица вероятностей точных счетов оставшегося времени
        prob_matrix = {}
        for i in range(max_goals_to_simulate):
            p_a = self._poisson_probability(i, rem_lambda_a)
            for j in range(max_goals_to_simulate):
                p_b = self._poisson_probability(j, rem_lambda_b)
                prob_matrix[(i, j)] = p_a * p_b

        p_win_a = 0.0
        p_draw = 0.0
        p_win_b = 0.0
        
        total_probs = {}
        # Карта вероятностей разности счетов для точного расчета Фор (Handicaps)
        # Ключ: (финальный_счет_А - финальный_счет_Б)
        diff_probs = {}

        for (rem_a, rem_b), p in prob_matrix.items():
            final_a = current_score_a + rem_a
            final_b = current_score_b + rem_b
            total_goals = final_a + final_b
            score_diff = final_a - final_b

            # 1Х2
            if final_a > final_b:
                p_win_a += p
            elif final_a == final_b:
                p_draw += p
            else:
                p_win_b += p

            # Тоталы и Форы
            total_probs[total_goals] = total_probs.get(total_goals, 0.0) + p
            diff_probs[score_diff] = diff_probs.get(score_diff, 0.0) + p

        p_win_a = max(p_win_a, 0.001)
        p_draw = max(p_draw, 0.001)
        p_win_b = max(p_win_b, 0.001)

        main_outcomes = [
            {"market_name": "1", "odds": round((1.0 / p_win_a) * self.margin, 2), "is_suspended": False},
            {"market_name": "X", "odds": round((1.0 / p_draw) * self.margin, 2), "is_suspended": False},
            {"market_name": "2", "odds": round((1.0 / p_win_b) * self.margin, 2), "is_suspended": False}
        ]

        # Формирование линейки Тоталов
        totals = []
        current_total_base = current_score_a + current_score_b
        for t_offset in [0.5, 1.5, 2.5]:
            target_total = current_total_base + t_offset
            p_under = sum(p for tg, p in total_probs.items() if tg < target_total)
            p_under = max(min(p_under, 0.999), 0.001)
            p_over = 1.0 - p_under
            p_over = max(min(p_over, 0.999), 0.001)

            totals.append({"market_name": f"TO {target_total}", "odds": round((1.0 / p_over) * self.margin, 2), "is_suspended": False})
            totals.append({"market_name": f"TU {target_total}", "odds": round((1.0 / p_under) * self.margin, 2), "is_suspended": False})

        # Новое: Формирование линейки Фор (Гандикапов) на основе матрицы разностей счетов
        handicaps = []
        current_diff_base = current_score_a - current_score_b
        
        # Генерируем 3 базовых коридора форы вокруг текущей разницы счетов
        for h_offset in [-1.5, -0.5, 0.5, 1.5]:
            target_handicap = current_diff_base + h_offset
            
            # Вероятность победы Команды А с учетом форы: (final_a - final_b + фора) > 0
            p_handicap_a = sum(p for diff, p in diff_probs.items() if (diff + h_offset) > 0)
            p_handicap_a = max(min(p_handicap_a, 0.999), 0.001)
            p_handicap_b = 1.0 - p_handicap_a
            p_handicap_b = max(min(p_handicap_b, 0.999), 0.001)

            # Форматируем знак форы для вывода на фронтенд
            sign_a = f"+{h_offset}" if h_offset > 0 else str(h_offset)
            sign_b = f"+{-h_offset}" if -h_offset > 0 else str(-h_offset)

            handicaps.append({"market_name": f"H1 ({sign_a})", "odds": round((1.0 / p_handicap_a) * self.margin, 2), "is_suspended": False})
            handicaps.append({"market_name": f"H2 ({sign_b})", "odds": round((1.0 / p_handicap_b) * self.margin, 2), "is_suspended": False})

        return {
            "main_outcomes": main_outcomes,
            "totals": totals,
            "handicaps": handicaps
        }

    def calculate_high_score_line(self, 
                                  pace: float, 
                                  efficiency_a: float, 
                                  efficiency_b: float, 
                                  time_left_ratio: float, 
                                  current_score_a: int, 
                                  current_score_b: int) -> Dict[str, List[Dict[str, Any]]]:
        """
        Генерирует рынки (1-2, Тоталы, Форы) для высокорезультативных видов спорта (Баскетбол).
        Использует нормальную аппроксимацию.
        """
        possessions_left = pace * time_left_ratio
        exp_rem_a = (possessions_left / 2) * efficiency_a
        exp_rem_b = (possessions_left / 2) * efficiency_b

        proj_final_a = current_score_a + exp_rem_a
        proj_final_b = current_score_b + exp_rem_b
        variance = 12.0 
        
        diff = proj_final_a - proj_final_b
        p_win_a = 0.5 * (1 + math.erf(diff / (variance * math.sqrt(2))))
        p_win_a = max(min(p_win_a, 0.999), 0.001)
        p_win_b = 1.0 - p_win_a

        main_outcomes = [
            {"market_name": "1", "odds": round((1.0 / p_win_a) * self.margin, 2), "is_suspended": False},
            {"market_name": "2", "odds": round((1.0 / p_win_b) * self.margin, 2), "is_suspended": False}
        ]

        proj_total = proj_final_a + proj_final_b
        totals = []
        base_total = round(proj_total * 2) / 2 
        
        for offset in [-5.5, 0.0, 5.5]:
            target_total = base_total + offset
            z_score = (target_total - proj_total) / variance
            p_under = 0.5 * (1 + math.erf(z_score / math.sqrt(2)))
            p_under = max(min(p_under, 0.999), 0.001)
            p_over = 1.0 - p_under

            totals.append({"market_name": f"TO {target_total}", "odds": round((1.0 / p_over) * self.margin, 2), "is_suspended": False})
            totals.append({"market_name": f"TU {target_total}", "odds": round((1.0 / p_under) * self.margin, 2), "is_suspended": False})

        # Новое: Расчет линейки Фор для баскетбола через интеграл нормального распределения
        handicaps = []
        # Вычисляем базовую ожидаемую фору
        base_handicap = round(-diff * 2) / 2
        
        for offset in [-3.5, 0.0, 3.5]:
            h_val = base_handicap + offset
            # Сдвигаем математическое ожидание разности на значение форы
            z_score_h = (diff + h_val) / variance
            p_h1 = 0.5 * (1 + math.erf(z_score_h / math.sqrt(2)))
            p_h1 = max(min(p_h1, 0.999), 0.001)
            p_h2 = 1.0 - p_h1

            sign_h1 = f"+{h_val}" if h_val > 0 else str(h_val)
            sign_h2 = f"+{-h_val}" if -h_val > 0 else str(-h_val)

            handicaps.append({"market_name": f"H1 ({sign_h1})", "odds": round((1.0 / p_h1) * self.margin, 2), "is_suspended": False})
            handicaps.append({"market_name": f"H2 ({sign_h2})", "odds": round((1.0 / p_h2) * self.margin, 2), "is_suspended": False})

        return {
            "main_outcomes": main_outcomes,
            "totals": totals,
            "handicaps": handicaps
        }
