# ============================================
# Prizolov Sports AI - Football Analytics Module
# Version: 2.02 (+1.01: Major refactor, improved xG model, enhanced Dixon-Coles,
#                 safe math ops, extended live metrics, unified output format,
#                 better recommendations, WP/Elementor-ready structure)
#
# CHANGELOG (что сделано):
# - Улучшена модель xG (динамическая адаптация + стабилизация)
# - Улучшена Dixon–Coles коррекция (мягкая, безопасная, нормализуемая)
# - Улучшена live-модель (dominance, danger, momentum)
# - Добавлена защита от деления на ноль и некорректных данных
# - Улучшена логика рекомендаций (более точный выбор рынка)
# - Добавлен единый формат вывода под многоспортовый пайплайн
# - Добавлены расширенные метрики для сайта (WP/Elementor)
# - Улучшена обработка ошибок
# - Версия повышена на +1.01 (глобальные изменения)
#
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at cloud.amvera.ru
# ============================================

import math
import logging
import numpy as np
from typing import Dict, Any, Optional
from datetime import datetime
from scipy.stats import poisson

logger = logging.getLogger("PrizolovSportsAI.FootballAnalytics")


class FootballAnalyticsModule:
    """
    Профильный модуль футбольной аналитики.
    Использует xG-модель, Dixon–Coles коррекцию и live-корректировки.
    """

    def __init__(self, bookmaker_margin: float = 0.08):
        self.margin = bookmaker_margin

        # Базовые xG за 90 минут
        self.base_xg_per_90 = {"home": 1.35, "away": 1.15}

        # Домашнее преимущество
        self.home_advantage = 1.12

        # Максимальное количество голов в матрице
        self.max_goals = 7

    # ============================================================
    # POISSON + DIXON-COLES
    # ============================================================

    def _calculate_match_probabilities(self, xg_home: float, xg_away: float) -> Dict[str, float]:
        """
        Улучшенный расчёт вероятностей исходов с Dixon–Coles коррекцией.
        """
        p_home_win = p_draw = p_away_win = 0.0
        probs_matrix = np.zeros((self.max_goals + 1, self.max_goals + 1))

        # Базовая матрица Пуассона
        for i in range(self.max_goals + 1):
            for j in range(self.max_goals + 1):
                probs_matrix[i, j] = poisson.pmf(i, xg_home) * poisson.pmf(j, xg_away)

        # Dixon–Coles коррекция (мягкая)
        rho = 0.025
        for i in range(4):
            for j in range(4):
                if i == j:
                    probs_matrix[i, j] *= (1 + rho)

        # Нормализация
        probs_matrix /= probs_matrix.sum()

        # Агрегация вероятностей
        for i in range(self.max_goals + 1):
            for j in range(self.max_goals + 1):
                prob = probs_matrix[i, j]
                if i > j:
                    p_home_win += prob
                elif i == j:
                    p_draw += prob
                else:
                    p_away_win += prob

        return {"home": p_home_win, "draw": p_draw, "away": p_away_win}

    # ============================================================
    # LIVE ADJUSTMENTS
    # ============================================================

    def _apply_live_adjustments(self, probs: Dict[str, float], tracking: Dict, elapsed: int) -> Dict[str, float]:
        """
        Live-корректировки вероятностей.
        """
        # Матч почти закончен
        if elapsed >= 5400:
            return {
                "home": 1.0 if probs["home"] > 0.5 else 0.0,
                "draw": 0.0,
                "away": 0.0
            }

        return self._apply_live_adjustments_original(probs, tracking, elapsed)

    def _apply_live_adjustments_original(self, probs: Dict[str, float], tracking: Dict, elapsed: int) -> Dict[str, float]:
        time_decay = max(0.2, 1.0 - (elapsed / 5400))

        dominance = tracking.get("recent_dominance_ratio", 0.5)
        danger_diff = tracking.get("danger_attacks_a", 0) - tracking.get("danger_attacks_b", 0)

        momentum = max(-0.15, min(0.15, (dominance - 0.5) * 0.3 + danger_diff * 0.02))

        adj_home = max(0.05, min(0.95, probs["home"] + momentum * time_decay))
        adj_away = max(0.05, min(0.95, probs["away"] - momentum * 0.8 * time_decay))
        adj_draw = max(0.05, 1.0 - adj_home - adj_away)

        total = adj_home + adj_draw + adj_away
        return {
            "home": adj_home / total,
            "draw": adj_draw / total,
            "away": adj_away / total
        }

    # ============================================================
    # MAIN ANALYSIS
    # ============================================================

    def analyze(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Главная функция анализа футбольного матча.
        """
        try:
            elapsed = context.get("elapsed_seconds", 0)
            tracking = context.get("tracking_data", {})
            game_time = context.get("game_time", "00:00")
            match_id = context.get("match_id", "unknown")

            # -----------------------------
            # BASE XG MODEL
            # -----------------------------
            time_factor = min(1.0, elapsed / 5400)

            base_xg_h = self.base_xg_per_90["home"] * time_factor * self.home_advantage
            base_xg_a = self.base_xg_per_90["away"] * time_factor

            live_xg_h = tracking.get("live_xg_a", 0.0)
            live_xg_a = tracking.get("live_xg_b", 0.0)

            # Стабилизированная модель xG
            effective_xg_h = max(0.1, base_xg_h + (live_xg_h - base_xg_h) * 0.7)
            effective_xg_a = max(0.1, base_xg_a + (live_xg_a - base_xg_a) * 0.7)

            # -----------------------------
            # PROBABILITIES
            # -----------------------------
            raw_probs = self._calculate_match_probabilities(effective_xg_h, effective_xg_a)
            live_probs = self._apply_live_adjustments(raw_probs, tracking, elapsed)

            # -----------------------------
            # RECOMMENDATIONS
            # -----------------------------
            candidates = []
            coefs = self._probs_to_coef(live_probs, self.margin)

            for market, key in [("П1", "home"), ("X", "draw"), ("П2", "away")]:
                if coefs.get(key, 0) >= 1.60:
                    candidates.append((market, coefs[key], live_probs[key]))

            # Тотал 2.5
            total_xg = effective_xg_h + effective_xg_a
            p_over = 1 - poisson.cdf(2, total_xg)
            coef_over = max(1.01, round(1.0 / (p_over * (1 + self.margin)), 2))

            if coef_over >= 1.60:
                candidates.append(("ТБ 2.5", coef_over, p_over))

            # Если нет хороших вариантов — берём лучший по вероятности
            if not candidates:
                best = max(live_probs, key=live_probs.get)
                market_map = {"home": "П1", "draw": "X", "away": "П2"}
                candidates.append((market_map[best], 1.65, live_probs[best]))

            market, coef, prob = max(candidates, key=lambda x: x[2])
            confidence = "high" if prob > 0.60 else ("medium" if prob > 0.45 else "low")

            return {
                "match_id": match_id,
                "line": market,
                "coefficient": coef,
                "probability": round(prob, 2),
                "confidence": confidence,
                "game_time": game_time,
                "xg_home": round(effective_xg_h, 2),
                "xg_away": round(effective_xg_a, 2),
                "generated_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"💥 FootballAnalyticsModule.analyze() failed: {e}")
            return None

    # ============================================================
    # COEFFICIENTS
    # ============================================================

    def _probs_to_coef(self, probs: Dict[str, float], margin: float) -> Dict[str, float]:
        """Преобразование вероятностей в коэффициенты."""
        adj_probs = {k: p * (1 + margin) for k, p in probs.items()}
        return {
            k: max(1.01, round(1.0 / p, 2))
            for k, p in adj_probs.items()
            if p > 0.01
        }
