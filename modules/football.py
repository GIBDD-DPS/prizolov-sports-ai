# ============================================
# Prizolov Sports AI - Football Analytics Module
# Version: 1.01 (+0.01: Improved Poisson + Dixon-Coles correction, better xG, recommendations)
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
    def __init__(self, bookmaker_margin: float = 0.08):
        self.margin = bookmaker_margin
        self.base_xg_per_90 = {"home": 1.35, "away": 1.15}
        self.home_advantage = 1.12
        self.max_goals = 7

    def _poisson_prob(self, lambda_: float, k: int) -> float:
        """Оригинальная функция Пуассона"""
        if lambda_ <= 0:
            return 0.0 if k > 0 else 1.0
        return (math.exp(-lambda_) * (lambda_ ** k)) / math.factorial(k)

    def _calculate_match_probabilities(self, xg_home: float, xg_away: float) -> Dict[str, float]:
        """Улучшенный расчёт с Dixon-Coles-like корректировкой"""
        p_home_win = p_draw = p_away_win = 0.0
        probs_matrix = np.zeros((self.max_goals + 1, self.max_goals + 1))

        for i in range(self.max_goals + 1):
            for j in range(self.max_goals + 1):
                prob = poisson.pmf(i, xg_home) * poisson.pmf(j, xg_away)
                probs_matrix[i, j] = prob

        # Dixon-Coles корректировка
        rho = 0.025
        for i in range(0, 4):
            for j in range(0, 4):
                if i == j:
                    probs_matrix[i, j] *= (1 + rho)

        probs_matrix /= probs_matrix.sum()

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

    def _apply_live_adjustments(self, probs: Dict[str, float], tracking: Dict, elapsed: int) -> Dict[str, float]:
        """Оставляем оригинальную логику live-корректировок"""
        if elapsed >= 5400:
            return {"home": 1.0 if probs["home"] > 0.5 else 0.0, "draw": 0.0, "away": 0.0}

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
        return {"home": adj_home / total, "draw": adj_draw / total, "away": adj_away / total}

    def analyze(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            elapsed = context.get("elapsed_seconds", 0)
            tracking = context.get("tracking_data", {})
            game_time = context.get("game_time", "00:00")
            match_id = context.get("match_id", "unknown")

            time_factor = min(1.0, elapsed / 5400)
            base_xg_h = self.base_xg_per_90["home"] * time_factor * self.home_advantage
            base_xg_a = self.base_xg_per_90["away"] * time_factor

            live_xg_h = tracking.get("live_xg_a", 0.0)
            live_xg_a = tracking.get("live_xg_b", 0.0)

            effective_xg_h = max(0.1, base_xg_h + (live_xg_h - base_xg_h) * 0.7)
            effective_xg_a = max(0.1, base_xg_a + (live_xg_a - base_xg_a) * 0.7)

            raw_probs = self._calculate_match_probabilities(effective_xg_h, effective_xg_a)
            live_probs = self._apply_live_adjustments(raw_probs, tracking, elapsed)

            # === Рекомендации (улучшено) ===
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

    def _probs_to_coef(self, probs: Dict[str, float], margin: float) -> Dict[str, float]:
        """Оригинальная функция"""
        adj_probs = {k: p * (1 + margin) for k, p in probs.items()}
        return {k: max(1.01, round(1.0 / p, 2)) for k, p in adj_probs.items() if p > 0.01}
