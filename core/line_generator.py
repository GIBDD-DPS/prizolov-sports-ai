# ============================================
# Prizolov Sports AI - Core Broad Line Generator
# Version: 6.00 (Unified Markets, Combo Matrix, Asian Engine)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at prizolov.ru
# ============================================

import math
from typing import Dict, Any, List, Tuple


class BroadLineGenerator:
    """
    Математический движок для расчета динамических букмекерских котировок:
    - основные исходы
    - тоталы
    - форы / азиатские гандикапы
    - комбинированные рынки (исход + тотал, исход + BTTS, и т.д.)
    """

    def __init__(self, default_margin: float = 1.05):
        # Глобальный мультипликатор маржи (может быть переопределён по типу рынка)
        self.margin = default_margin

    # ============================================================
    # ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
    # ============================================================

    @staticmethod
    def _poisson_probability(k: int, lmbda: float) -> float:
        """P(X = k) для распределения Пуассона."""
        if lmbda <= 0:
            return 1.0 if k == 0 else 0.0
        try:
            return (lmbda ** k * math.exp(-lmbda)) / math.factorial(k)
        except OverflowError:
            return 0.0

    @staticmethod
    def _clamp_prob(p: float) -> float:
        """Ограничение вероятности в безопасном диапазоне."""
        return max(min(p, 0.999), 0.001)

    def _price(self, p: float, margin: float = None) -> Tuple[float, float]:
        """Перевод вероятности в коэффициент с учётом маржи."""
        p = self._clamp_prob(p)
        m = margin if margin is not None else self.margin
        odds = (1.0 / p) * m
        return round(odds, 2), p

    # ============================================================
    # ОСНОВНАЯ ФУТБОЛЬНАЯ ЛИНИЯ ПО ПУАССОНУ
    # ============================================================

    def calculate_poisson_line(
        self,
        lambda_team_a: float,
        lambda_team_b: float,
        time_left_ratio: float,
        current_score_a: int,
        current_score_b: int,
        max_goals_to_simulate: int = 15
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Генерирует рынки по Пуассону:
        - основные исходы
        - тоталы
        - азиатские тоталы
        - форы / азиатские гандикапы
        - комбинированные рынки (исход + тотал, исход + BTTS, и т.д.)
        """

        # Оставшаяся интенсивность голов
        rem_lambda_a = max(lambda_team_a * time_left_ratio, 0.01)
        rem_lambda_b = max(lambda_team_b * time_left_ratio, 0.01)

        # Матрица вероятностей оставшихся голов
        prob_matrix: Dict[Tuple[int, int], float] = {}
        for i in range(max_goals_to_simulate):
            p_a = self._poisson_probability(i, rem_lambda_a)
            for j in range(max_goals_to_simulate):
                p_b = self._poisson_probability(j, rem_lambda_b)
                prob_matrix[(i, j)] = p_a * p_b

        # Агрегированные распределения
        p_win_a = p_draw = p_win_b = 0.0
        total_probs: Dict[int, float] = {}
        diff_probs: Dict[int, float] = {}
        it_probs_a: Dict[int, float] = {}
        it_probs_b: Dict[int, float] = {}

        # Для комбинированных рынков
        p_w1_and_over_25 = p_w1_and_under_25 = 0.0
        p_w2_and_over_25 = p_w2_and_under_25 = 0.0
        p_btts_yes = 0.0

        for (rem_a, rem_b), p in prob_matrix.items():
            final_a = current_score_a + rem_a
            final_b = current_score_b + rem_b
            total_goals = final_a + final_b
            score_diff = final_a - final_b

            # Основные исходы
            if final_a > final_b:
                p_win_a += p
                if total_goals > 2.5:
                    p_w1_and_over_25 += p
                else:
                    p_w1_and_under_25 += p
            elif final_a == final_b:
                p_draw += p
            else:
                p_win_b += p
                if total_goals > 2.5:
                    p_w2_and_over_25 += p
                else:
                    p_w2_and_under_25 += p

            # Тоталы
            total_probs[total_goals] = total_probs.get(total_goals, 0.0) + p

            # Разница
            diff_probs[score_diff] = diff_probs.get(score_diff, 0.0) + p

            # Индивидуальные тоталы
            it_probs_a[final_a] = it_probs_a.get(final_a, 0.0) + p
            it_probs_b[final_b] = it_probs_b.get(final_b, 0.0) + p

            # BTTS
            if final_a > 0 and final_b > 0:
                p_btts_yes += p

        p_btts_yes = self._clamp_prob(p_btts_yes)
        p_btts_no = self._clamp_prob(1.0 - p_btts_yes)

        # Нормализация основных исходов
        p_win_a = self._clamp_prob(p_win_a)
        p_draw = self._clamp_prob(p_draw)
        p_win_b = self._clamp_prob(p_win_b)

        markets: List[Dict[str, Any]] = []

        # --------------------------------------------------------
        # MAIN OUTCOMES
        # --------------------------------------------------------
        odds_1, p1 = self._price(p_win_a)
        odds_x, px = self._price(p_draw)
        odds_2, p2 = self._price(p_win_b)

        markets.extend([
            {"type": "main", "market_name": "1", "odds": odds_1, "probability": p1, "is_suspended": False},
            {"type": "main", "market_name": "X", "odds": odds_x, "probability": px, "is_suspended": False},
            {"type": "main", "market_name": "2", "odds": odds_2, "probability": p2, "is_suspended": False},
        ])

        # --------------------------------------------------------
        # TOTALS (классические)
        # --------------------------------------------------------
        current_total_base = current_score_a + current_score_b
        for t_offset in [0.5, 1.5, 2.5]:
            target_total = current_total_base + t_offset
            p_under = sum(p for tg, p in total_probs.items() if tg < target_total)
            p_under = self._clamp_prob(p_under)
            p_over = self._clamp_prob(1.0 - p_under)

            odds_over, po = self._price(p_over)
            odds_under, pu = self._price(p_under)

            markets.append({
                "type": "total",
                "market_name": f"TO {target_total}",
                "odds": odds_over,
                "probability": po,
                "is_suspended": False
            })
            markets.append({
                "type": "total",
                "market_name": f"TU {target_total}",
                "odds": odds_under,
                "probability": pu,
                "is_suspended": False
            })

        # --------------------------------------------------------
        # ASIAN HANDICAPS (простая матрица вокруг текущей разницы)
        # --------------------------------------------------------
        handicaps = []
        current_diff_base = current_score_a - current_score_b

        # Базовые линии фор вокруг текущей разницы
        for h in [-1.0, -0.5, 0.0, 0.5, 1.0]:
            # P(H1 выигрывает с форой h) = P(diff + h > 0)
            p_h1 = sum(p for diff, p in diff_probs.items() if (diff + h) > 0)
            p_h1 = self._clamp_prob(p_h1)
            p_h2 = self._clamp_prob(1.0 - p_h1)

            sign_a = f"+{h}" if h > 0 else str(h)
            sign_b = f"+{-h}" if -h > 0 else str(-h)

            odds_h1, ph1 = self._price(p_h1)
            odds_h2, ph2 = self._price(p_h2)

            handicaps.append({
                "type": "handicap",
                "market_name": f"H1 ({sign_a})",
                "odds": odds_h1,
                "probability": ph1,
                "is_suspended": False
            })
            handicaps.append({
                "type": "handicap",
                "market_name": f"H2 ({sign_b})",
                "odds": odds_h2,
                "probability": ph2,
                "is_suspended": False
            })

        markets.extend(handicaps)

        # --------------------------------------------------------
        # ASIAN TOTALS (.25 / .75)
        # --------------------------------------------------------
        asian_totals = []
        for base_t in [current_total_base + 1, current_total_base + 2]:
            # Линия T+0.25 = среднее между T и T+0.5
            t_25 = base_t + 0.25
            p_under_t = sum(p for tg, p in total_probs.items() if tg < base_t)
            p_under_t05 = sum(p for tg, p in total_probs.items() if tg < (base_t + 0.5))
            p_under_comb = self._clamp_prob((p_under_t + p_under_t05) / 2.0)
            p_over_comb = self._clamp_prob(1.0 - p_under_comb)

            odds_over, po = self._price(p_over_comb)
            odds_under, pu = self._price(p_under_comb)

            asian_totals.append({
                "type": "total",
                "market_name": f"TO {t_25}",
                "odds": odds_over,
                "probability": po,
                "is_suspended": False
            })
            asian_totals.append({
                "type": "total",
                "market_name": f"TU {t_25}",
                "odds": odds_under,
                "probability": pu,
                "is_suspended": False
            })

        markets.extend(asian_totals)

        # --------------------------------------------------------
        # COMBO MARKETS (26 рынков)
        # --------------------------------------------------------

        # 1) W1/W2 + Over/Under 2.5 (уже есть p_w1_and_over_25 и т.п.)
        combo_markets: List[Dict[str, Any]] = []

        for name, p_val in [
            ("W1 & Over 2.5", p_w1_and_over_25),
            ("W1 & Under 2.5", p_w1_and_under_25),
            ("W2 & Over 2.5", p_w2_and_over_25),
            ("W2 & Under 2.5", p_w2_and_under_25),
        ]:
            odds, p = self._price(p_val)
            combo_markets.append({
                "type": "combo",
                "market_name": name,
                "odds": odds,
                "probability": p,
                "is_suspended": False
            })

        # 2) BTTS Yes/No
        odds_btts_yes, p_yes = self._price(p_btts_yes)
        odds_btts_no, p_no = self._price(p_btts_no)

        combo_markets.append({
            "type": "combo",
            "market_name": "BTTS Yes",
            "odds": odds_btts_yes,
            "probability": p_yes,
            "is_suspended": False
        })
        combo_markets.append({
            "type": "combo",
            "market_name": "BTTS No",
            "odds": odds_btts_no,
            "probability": p_no,
            "is_suspended": False
        })

        # Для комбинированных исходов с BTTS и Over/Under нам нужны дополнительные интеграции
        # BTTS + исход
        p_w1_btts_yes = p_w1_btts_no = 0.0
        p_w2_btts_yes = p_w2_btts_no = 0.0
        p_x_btts_yes = p_x_btts_no = 0.0

        # Over 1.5 / 2.5 + исход, Over 2.5 + BTTS
        p_w1_over15 = p_w1_under15 = 0.0
        p_w2_over15 = p_w2_under15 = 0.0
        p_over25_btts_yes = p_over25_btts_no = 0.0

        # Double chance + Over/Under 2.5
        p_1x_over25 = p_1x_under25 = 0.0
        p_x2_over25 = p_x2_under25 = 0.0
        p_12_over25 = p_12_under25 = 0.0

        # DNB + Over/Under 2.5
        p_dnb1_over25 = p_dnb1_under25 = 0.0
        p_dnb2_over25 = p_dnb2_under25 = 0.0

        for (rem_a, rem_b), p in prob_matrix.items():
            fa = current_score_a + rem_a
            fb = current_score_b + rem_b
            tg = fa + fb

            is_w1 = fa > fb
            is_x = fa == fb
            is_w2 = fa < fb
            is_btts = (fa > 0 and fb > 0)

            # BTTS + исход
            if is_w1 and is_btts:
                p_w1_btts_yes += p
            if is_w1 and not is_btts:
                p_w1_btts_no += p
            if is_w2 and is_btts:
                p_w2_btts_yes += p
            if is_w2 and not is_btts:
                p_w2_btts_no += p
            if is_x and is_btts:
                p_x_btts_yes += p
            if is_x and not is_btts:
                p_x_btts_no += p

            # W1/W2 + Over/Under 1.5
            if is_w1:
                if tg > 1.5:
                    p_w1_over15 += p
                else:
                    p_w1_under15 += p
            if is_w2:
                if tg > 1.5:
                    p_w2_over15 += p
                else:
                    p_w2_under15 += p

            # Over 2.5 + BTTS
            if tg > 2.5 and is_btts:
                p_over25_btts_yes += p
            if tg > 2.5 and not is_btts:
                p_over25_btts_no += p

            # Double chance + Over/Under 2.5
            if (is_w1 or is_x):
                if tg > 2.5:
                    p_1x_over25 += p
                else:
                    p_1x_under25 += p
            if (is_w2 or is_x):
                if tg > 2.5:
                    p_x2_over25 += p
                else:
                    p_x2_under25 += p
            if (is_w1 or is_w2):
                if tg > 2.5:
                    p_12_over25 += p
                else:
                    p_12_under25 += p

            # DNB + Over/Under 2.5 (ничья → возврат, не учитываем)
            if is_w1:
                if tg > 2.5:
                    p_dnb1_over25 += p
                else:
                    p_dnb1_under25 += p
            if is_w2:
                if tg > 2.5:
                    p_dnb2_over25 += p
                else:
                    p_dnb2_under25 += p

        # Нормируем и добавляем все комбинированные рынки

        def add_combo(name: str, p_val: float):
            odds, p = self._price(p_val)
            combo_markets.append({
                "type": "combo",
                "market_name": name,
                "odds": odds,
                "probability": p,
                "is_suspended": False
            })

        # W1/W2 + BTTS
        add_combo("W1 & BTTS Yes", p_w1_btts_yes)
        add_combo("W1 & BTTS No", p_w1_btts_no)
        add_combo("W2 & BTTS Yes", p_w2_btts_yes)
        add_combo("W2 & BTTS No", p_w2_btts_no)
        add_combo("Draw & BTTS Yes", p_x_btts_yes)
        add_combo("Draw & BTTS No", p_x_btts_no)

        # W1/W2 + Over/Under 1.5
        add_combo("W1 & Over 1.5", p_w1_over15)
        add_combo("W1 & Under 1.5", p_w1_under15)
        add_combo("W2 & Over 1.5", p_w2_over15)
        add_combo("W2 & Under 1.5", p_w2_under15)

        # Double chance + Over/Under 2.5
        add_combo("1X & Over 2.5", p_1x_over25)
        add_combo("1X & Under 2.5", p_1x_under25)
        add_combo("X2 & Over 2.5", p_x2_over25)
        add_combo("X2 & Under 2.5", p_x2_under25)
        add_combo("12 & Over 2.5", p_12_over25)
        add_combo("12 & Under 2.5", p_12_under25)

        # DNB + Over/Under 2.5
        add_combo("DNB1 & Over 2.5", p_dnb1_over25)
        add_combo("DNB1 & Under 2.5", p_dnb1_under25)
        add_combo("DNB2 & Over 2.5", p_dnb2_over25)
        add_combo("DNB2 & Under 2.5", p_dnb2_under25)

        # Over 2.5 & BTTS Yes/No
        add_combo("Over 2.5 & BTTS Yes", p_over25_btts_yes)
        add_combo("Over 2.5 & BTTS No", p_over25_btts_no)

        markets.extend(combo_markets)

        return {"markets": markets}

    # ============================================================
    # БАСКЕТБОЛЬНАЯ ЛИНИЯ (НОРМАЛЬНОЕ РАСПРЕДЕЛЕНИЕ)
    # ============================================================

    def calculate_high_score_line(
        self,
        pace: float,
        efficiency_a: float,
        efficiency_b: float,
        time_left_ratio: float,
        current_score_a: int,
        current_score_b: int
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Расчет баскетбольной линии по нормальному распределению:
        - основные исходы
        - гандикапы
        (тоталы можно добавить аналогично)
        """

        possessions_left = pace * time_left_ratio
        if possessions_left <= 0:
            possessions_left = 0.01

        exp_rem_a = (possessions_left / 2.0) * efficiency_a
        exp_rem_b = (possessions_left / 2.0) * efficiency_b

        proj_final_a = current_score_a + exp_rem_a
        proj_final_b = current_score_b + exp_rem_b

        variance = 12.0  # эмпирический параметр разброса

        diff = proj_final_a - proj_final_b
        z = diff / (variance * math.sqrt(2))
        p_win_a = 0.5 * (1 + math.erf(z))
        p_win_a = self._clamp_prob(p_win_a)
        p_win_b = self._clamp_prob(1.0 - p_win_a)

        markets: List[Dict[str, Any]] = []

        # Основные исходы
        odds_1, p1 = self._price(p_win_a)
        odds_2, p2 = self._price(p_win_b)

        markets.append({
            "type": "main",
            "market_name": "1",
            "odds": odds_1,
            "probability": p1,
            "is_suspended": False
        })
        markets.append({
            "type": "main",
            "market_name": "2",
            "odds": odds_2,
            "probability": p2,
            "is_suspended": False
        })

        # Гандикапы
        handicaps: List[Dict[str, Any]] = []
        base_handicap = round(-diff * 2) / 2  # округление к ближайшей 0.5

        for offset in [-1.25, -0.25, 0.25, 1.25]:
            h_val = base_handicap + offset
            z_h = (diff + h_val) / (variance * math.sqrt(2))
            p_h1 = 0.5 * (1 + math.erf(z_h))
            p_h1 = self._clamp_prob(p_h1)
            p_h2 = self._clamp_prob(1.0 - p_h1)

            sign_h1 = f"+{h_val}" if h_val > 0 else str(h_val)
            sign_h2 = f"+{-h_val}" if -h_val > 0 else str(-h_val)

            odds_h1, ph1 = self._price(p_h1)
            odds_h2, ph2 = self._price(p_h2)

            handicaps.append({
                "type": "handicap",
                "market_name": f"H1 ({sign_h1})",
                "odds": odds_h1,
                "probability": ph1,
                "is_suspended": False
            })
            handicaps.append({
                "type": "handicap",
                "market_name": f"H2 ({sign_h2})",
                "odds": odds_h2,
                "probability": ph2,
                "is_suspended": False
            })

        markets.extend(handicaps)

        return {"markets": markets}
