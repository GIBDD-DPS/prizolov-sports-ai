# ============================================
# Prizolov Sports AI - Core Broad Line Generator
# Version: 3.09 (Asian Handicap Extended Matrix)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at prizolov.ru
# ============================================

import math
from typing import Dict, Any, List

class BroadLineGenerator:
    """Математический движок для расчета динамических букмекерских котировок (Исходы, Тоталы, Форы, Азиатские маркеты)"""

    def __init__(self, default_margin: float = 1.05):
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
        """Генерирует классические, комбинированные, интервальные и азиатские рынки по Пуассону"""
        rem_lambda_a = max(lambda_team_a * time_left_ratio, 0.01)
        rem_lambda_b = max(lambda_team_b * time_left_ratio, 0.01)

        prob_matrix = {}
        for i in range(max_goals_to_simulate):
            p_a = self._poisson_probability(i, rem_lambda_a)
            for j in range(max_goals_to_simulate):
                p_b = self._poisson_probability(j, rem_lambda_b)
                prob_matrix[(i, j)] = p_a * p_b

        p_win_a, p_draw, p_win_b = 0.0, 0.0, 0.0
        total_probs, diff_probs = {}, {}
        it_probs_a, it_probs_b = {}, {}
        
        p_w1_and_over_25, p_w1_and_under_25 = 0.0, 0.0
        p_w2_and_over_25, p_w2_and_under_25 = 0.0, 0.0

        for (rem_a, rem_b), p in prob_matrix.items():
            final_a = current_score_a + rem_a
            final_b = current_score_b + rem_b
            total_goals = final_a + final_b
            score_diff = final_a - final_b

            if final_a > final_b:
                p_win_a += p
                if total_goals > 2.5: p_w1_and_over_25 += p
                else: p_w1_and_under_25 += p
            elif final_a == final_b:
                p_draw += p
            else:
                p_win_b += p
                if total_goals > 2.5: p_w2_and_over_25 += p
                else: p_w2_and_under_25 += p

            total_probs[total_goals] = total_probs.get(total_goals, 0.0) + p
            diff_probs[score_diff] = diff_probs.get(score_diff, 0.0) + p
            it_probs_a[final_a] = it_probs_a.get(final_a, 0.0) + p
            it_probs_b[final_b] = it_probs_b.get(final_b, 0.0) + p

        p_win_a = max(p_win_a, 0.001)
        p_draw = max(p_draw, 0.001)
        p_win_b = max(p_win_b, 0.001)

        main_outcomes = [
            {"market_name": "1", "odds": round((1.0 / p_win_a) * self.margin, 2), "is_suspended": False},
            {"market_name": "X", "odds": round((1.0 / p_draw) * self.margin, 2), "is_suspended": False},
            {"market_name": "2", "odds": round((1.0 / p_win_b) * self.margin, 2), "is_suspended": False}
        ]

        totals = []
        current_total_base = current_score_a + current_score_b
        
        for t_offset in [0.5, 1.5, 2.5]:
            target_total = current_total_base + t_offset
            p_under = sum(p for tg, p in total_probs.items() if tg < target_total)
            p_under = max(min(p_under, 0.999), 0.001)
            p_over = max(1.0 - p_under, 0.001)

            totals.append({"market_name": f"TO {target_total}", "odds": round((1.0 / p_over) * self.margin, 2), "is_suspended": False})
            totals.append({"market_name": f"TU {target_total}", "odds": round((1.0 / p_under) * self.margin, 2), "is_suspended": False})

        # Новое: Расчет расширенной азиатской матрицы Фор (Гандикапов) с шагом 0.25 и 0.75
        handicaps = []
        current_diff_base = current_score_a - current_score_b
        
        # Массив целевых смещений для расчета азиатских фор
        # Например, фора -0.25 рассчитывается как среднее между 0.0 и -0.5
        for h_base in [-1.0, 0.0, 1.0]:
            for quarter in [-0.25, 0.25]:
                target_h = current_diff_base + h_base + quarter
                
                # Смежные стандартные форы
                left_h = h_base + quarter - 0.25
                right_h = h_base + quarter + 0.25
                
                # Интегрируем вероятности по матрице разностей счетов
                p_h1_left = sum(p for diff, p in diff_probs.items() if (diff + left_h) > 0)
                p_h1_right = sum(p for diff, p in diff_probs.items() if (diff + right_h) > 0)
                
                p_h1_comb = (p_h1_left + p_h1_right) / 2.0
                p_h1_comb = max(min(p_h1_comb, 0.999), 0.001)
                p_h2_comb = max(1.0 - p_h1_comb, 0.001)
                
                sign_a = f"+{target_h}" if target_h > 0 else str(target_h)
                sign_b = f"+{-target_h}" if -target_h > 0 else str(-target_h)

                handicaps.append({"market_name": f"H1 ({sign_a})", "odds": round((1.0 / p_h1_comb) * self.margin, 2), "is_suspended": False})
                handicaps.append({"market_name": f"H2 ({sign_b})", "odds": round((1.0 / p_h2_comb) * self.margin, 2), "is_suspended": False})

        # Стандартные азиатские тоталы .25 и .75
        asian_totals = []
        for base_t in [current_total_base + 1, current_total_base + 2]:
            t_25 = base_t + 0.25
            p_under_20 = sum(p for tg, p in total_probs.items() if tg < base_t)
            p_under_25 = sum(p for tg, p in total_probs.items() if tg < (base_t + 0.5))
            p_under_comb = (p_under_20 + p_under_25) / 2.0
            p_over_comb = max(1.0 - p_under_comb, 0.001)
            
            asian_totals.append({"market_name": f"TO {t_25}", "odds": round((1.0 / p_over_comb) * self.margin, 2), "is_suspended": False})
            asian_totals.append({"market_name": f"TU {t_25}", "odds": round((1.0 / max(p_under_comb, 0.001)) * self.margin, 2), "is_suspended": False})

        return {
            "main_outcomes": main_outcomes,
            "totals": totals + combo_markets + asian_totals,
            "handicaps": handicaps
        }

    def calculate_high_score_line(self, pace: float, efficiency_a: float, efficiency_b: float, time_left_ratio: float, current_score_a: int, current_score_b: int) -> Dict[str, List[Dict[str, Any]]]:
        """Расчет баскетбольной линии по нормальному распределению"""
        possessions_left = possessions_left_val if (possessions_left_val := pace * time_left_ratio) > 0 else 0.01
        exp_rem_a = (possessions_left / 2) * efficiency_a
        exp_rem_b = (possessions_left / 2) * efficiency_b

        proj_final_a = current_score_a + exp_rem_a
        proj_final_b = current_score_b + exp_rem_b
        variance = 12.0
        
        diff = proj_final_a - proj_final_b
        p_win_a = 0.5 * (1 + math.erf(diff / (variance * math.sqrt(2))))
        p_win_a = max(min(p_win_a, 0.999), 0.001)
        p_win_b = max(1.0 - p_win_a, 0.001)

        main_outcomes = [
            {"market_name": "1", "odds": round((1.0 / p_win_a) * self.margin, 2), "is_suspended": False},
            {"market_name": "2", "odds": round((1.0 / p_win_b) * self.margin, 2), "is_suspended": False}
        ]

        # Расчет гандикапов для баскетбола
        handicaps = []
        base_handicap = round(-diff * 2) / 2
        for offset in [-1.25, -0.25, 0.25, 1.25]:
            h_val = base_handicap + offset
            z_score_h = (diff + h_val) / variance
            p_h1 = 0.5 * (1 + math.erf(z_score_h / math.sqrt(2)))
            p_h1 = max(min(p_h1, 0.999), 0.001)
            p_h2 = max(1.0 - p_h1, 0.001)

            sign_h1 = f"+{h_val}" if h_val > 0 else str(h_val)
            sign_h2 = f"+{-h_val}" if -h_val > 0 else str(-h_val)

            handicaps.append({"market_name": f"H1 ({sign_h1})", "odds": round((1.0 / p_h1) * self.margin, 2), "is_suspended": False})
            handicaps.append({"market_name": f"H2 ({sign_h2})", "odds": round((1.0 / p_h2) * self.margin, 2), "is_suspended": False})

        return {"main_outcomes": main_outcomes, "totals": [], "handicaps": handicaps}
