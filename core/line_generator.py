# ============================================
# Prizolov Sports AI - Core Broad Line Generator
# Version: 3.05 (Interval Markets Analytics Core)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at prizolov.ru
# ============================================

import math
from typing import Dict, Any, List

class BroadLineGenerator:
    """Математический движок для расчета динамических коэффициентов спортивной линии (Исходы, Тоталы, Форы, ИТ, Комбо, Интервалы)"""

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
        Генерирует базовые, комбинированные и интервальные рынки на основе Пуассоновского распределения.
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
        diff_probs = {}
        it_probs_a = {}
        it_probs_b = {}
        
        p_w1_and_over_25 = 0.0
        p_w1_and_under_25 = 0.0
        p_w2_and_over_25 = 0.0
        p_w2_and_under_25 = 0.0

        for (rem_a, rem_b), p in prob_matrix.items():
            final_a = current_score_a + rem_a
            final_b = current_score_b + rem_b
            total_goals = final_a + final_b
            score_diff = final_a - final_b

            # 1Х2
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

            # Тоталы, Форы и Индивидуальные тоталы
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

        # Формирование линейки Фор
        handicaps = []
        current_diff_base = current_score_a - current_score_b
        for h_offset in [-1.5, -0.5, 0.5, 1.5]:
            target_handicap = current_diff_base + h_offset
            p_handicap_a = sum(p for diff, p in diff_probs.items() if (diff + h_offset) > 0)
            p_handicap_a = max(min(p_handicap_a, 0.999), 0.001)
            p_handicap_b = 1.0 - p_handicap_a
            p_handicap_b = max(min(p_handicap_b, 0.999), 0.001)

            sign_a = f"+{h_offset}" if h_offset > 0 else str(h_offset)
            sign_b = f"+{-h_offset}" if -h_offset > 0 else str(-h_offset)

            handicaps.append({"market_name": f"H1 ({sign_a})", "odds": round((1.0 / p_handicap_a) * self.margin, 2), "is_suspended": False})
            handicaps.append({"market_name": f"H2 ({sign_b})", "odds": round((1.0 / p_handicap_b) * self.margin, 2), "is_suspended": False})

        # Формирование линейки Индивидуальных тоталов
        for t_offset in [0.5, 1.5]:
            target_it_a = current_score_a + t_offset
            p_it_under_a = sum(p for goals, p in it_probs_a.items() if goals < target_it_a)
            p_it_under_a = max(min(p_it_under_a, 0.999), 0.001)
            p_it_over_a = max(1.0 - p_it_under_a, 0.001)
            
            totals.append({"market_name": f"IT1 O {target_it_a}", "odds": round((1.0 / p_it_over_a) * self.margin, 2), "is_suspended": False})
            totals.append({"market_name": f"IT1 U {target_it_a}", "odds": round((1.0 / p_it_under_a) * self.margin, 2), "is_suspended": False})
            
            target_it_b = current_score_b + t_offset
            p_it_under_b = sum(p for goals, p in it_probs_b.items() if goals < target_it_b)
            p_it_under_b = max(min(p_it_under_b, 0.999), 0.001)
            p_it_over_b = max(1.0 - p_it_over_b, 0.001)
            
            totals.append({"market_name": f"IT2 O {target_it_b}", "odds": round((1.0 / p_it_over_b) * self.margin, 2), "is_suspended": False})
            totals.append({"market_name": f"IT2 U {target_it_b}", "odds": round((1.0 / p_it_under_b) * self.margin, 2), "is_suspended": False})

        # Формирование комбинированных рынков
        p_w1_and_over_25 = max(p_w1_and_over_25, 0.001)
        p_w1_and_under_25 = max(p_w1_and_under_25, 0.001)
        p_w2_and_over_25 = max(p_w2_and_over_25, 0.001)
        p_w2_and_under_25 = max(p_w2_and_under_25, 0.001)

        combo_markets = [
            {"market_name": "1 + TO 2.5", "odds": round((1.0 / p_w1_and_over_25) * self.margin, 2), "is_suspended": False},
            {"market_name": "1 + TU 2.5", "odds": round((1.0 / p_w1_and_under_25) * self.margin, 2), "is_suspended": False},
            {"market_name": "2 + TO 2.5", "odds": round((1.0 / p_w2_and_over_25) * self.margin, 2), "is_suspended": False},
            {"market_name": "2 + TU 2.5", "odds": round((1.0 / p_w2_and_under_25) * self.margin, 2), "is_suspended": False}
        ]

        # Новое: Расчет Поминутных Интервальных рынков (например, гол в следующие 10 / 15 минут)
        # 10 минут — это примерно 1/9 часть футбольного матча (ratio_10 = 0.11)
        interval_ratio_15 = 0.166 # 15 минут от 90 минут матча
        
        # Суммарная текущая интенсивность гола в матче для обеих команд
        combined_lambda = rem_lambda_a + rem_lambda_b
        # Масштабируем интенсивность на 15-минутный отрезок времени
        interval_lambda = combined_lambda * (interval_ratio_15 / max(time_left_ratio, 0.01))
        
        # Вероятность того, что в следующие 15 минут будет забит ХОТЯ БЫ один гол (1 - вероятность 0 голов)
        p_no_goals_in_interval = self._poisson_probability(0, interval_lambda)
        p_goal_in_next_15_min = max(min(1.0 - p_no_goals_in_interval, 0.999), 0.001)
        p_no_goal_in_next_15_min = 1.0 - p_goal_in_next_15_min

        # Для интервальных экспресс-рынков закладываем повышенную маржу (+4%), страхуя риски дисперсии
        interval_margin = self.margin + 0.04
        interval_markets = [
            {"market_name": "Goal in next 15 min - Yes", "odds": round((1.0 / p_goal_in_next_15_min) * interval_margin, 2), "is_suspended": False},
            {"market_name": "Goal in next 15 min - No", "odds": round((1.0 / p_no_goal_in_next_15_min) * interval_margin, 2), "is_suspended": False}
        ]

        return {
            "main_outcomes": main_outcomes,
            "totals": totals + combo_markets + interval_markets, # Добавляем интервалы в общую структуру тоталов матча
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
        Генерирует рынки (1-2, Тоталы, Форы, ИТ) для высокорезультативных видов спорта (Баскетбол).
        Использует нормальную аппроксимацию.
        """
        possessions_left = pace * time_left_ratio
        exp_rem_a = (possessions_left / 2) * efficiency_a
        exp_rem_b = (possessions_left / 2) * efficiency_b

        proj_final_a = current_score_a + exp_rem_a
        proj_final_b = current_score_b + exp_rem_b
        
        variance = 12.0 
        ind_variance = variance / math.sqrt(2)
        
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

        # Расчет линейки Фор
        handicaps = []
        base_handicap = round(-diff * 2) / 2
        for offset in [-3.5, 0.0, 3.5]:
            h_val = base_handicap + offset
            z_score_h = (diff + h_val) / variance
            p_h1 = 0.5 * (1 + math.erf(z_score_h / math.sqrt(2)))
            p_h1 = max(min(p_h1, 0.999), 0.001)
            p_h2 = 1.0 - p_h1

            sign_h1 = f"+{h_val}" if h_val > 0 else str(h_val)
            sign_h2 = f"+{-h_val}" if -h_val > 0 else str(-h_val)

            handicaps.append({"market_name": f"H1 ({sign_h1})", "odds": round((1.0 / p_h1) * self.margin, 2), "is_suspended": False})
            handicaps.append({"market_name": f"H2 ({sign_h2})", "odds": round((1.0 / p_h2) * self.margin, 2), "is_suspended": False})

        # Расчет Индивидуальных Тоталов
        for offset in [-2.5, 2.5]:
            base_it_a = round(proj_final_a * 2) / 2 + offset
            z_score_it_a = (base_it_a - proj_final_a) / ind_variance
            p_under_it_a = 0.5 * (1 + math.erf(z_score_it_a / math.sqrt(2)))
            p_under_it_a = max(min(p_under_it_a, 0.999), 0.001)
            p_over_it_a = 1.0 - p_under_it_a
            
            totals.append({"market_name": f"IT1 O {base_it_a}", "odds": round((1.0 / p_over_it_a) * self.margin, 2), "is_suspended": False})
            totals.append({"market_name": f"IT1 U {base_it_a}", "odds": round((1.0 / p_under_it_a) * self.margin, 2), "is_suspended": False})

            base_it_b = round(proj_final_b * 2) / 2 + offset
            z_score_it_b = (base_it_b - proj_final_b) / ind_variance
            p_under_it_b = 0.5 * (1 + math.erf(z_score_it_b / math.sqrt(2)))
            p_under_it_b = max(min(p_under_it_b, 0.999), 0.001)
            p_over_it_b = 1.0 - p_under_it_b
            
            totals.append({"market_name": f"IT2 O {base_it_b}", "odds": round((1.0 / p_over_it_b) * self.margin, 2), "is_suspended": False})
            totals.append({"market_name": f"IT2 U {base_it_b}", "odds": round((1.0 / p_under_it_b) * self.margin, 2), "is_suspended": False})

        return {
            "main_outcomes": main_outcomes,
            "totals": totals,
            "handicaps": handicaps
        }
