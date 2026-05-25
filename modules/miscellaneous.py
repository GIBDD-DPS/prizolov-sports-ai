# ============================================
# Prizolov Sports AI - Miscellaneous Sports Module
# Version: 4.03 (+1.01: Major refactor, unified output format, improved model selection,
#                 safe math ops, extended metrics, better momentum model,
#                 improved Poisson/Normal logic, WP/Elementor-ready structure)
#
# CHANGELOG (что сделано):
# - Улучшена логика выбора модели (Poisson / High-Score Normal)
# - Улучшена модель momentum и live_strength
# - Добавлена защита от деления на ноль и некорректных данных
# - Улучшена модель тоталов и статистики
# - Улучшена структура active_specials
# - Добавлен единый формат line_data (как в других видах спорта)
# - Улучшена модель владения (possession)
# - Улучшена обработка ошибок
# - Подготовка под WordPress/Elementor
# - Версия повышена на +1.01 (глобальные изменения)
#
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at prizolov.ru
# ============================================

import numpy as np
from typing import Dict, Any
from core.line_generator import BroadLineGenerator


class MiscellaneousSportsModule:
    """
    Универсальный ИИ-модуль для генерации линий на любые виды спорта.
    Используется для категории "Разное" в многоспортовом пайплайне.
    """

    def __init__(self, match_id: str = "unknown", sport_name: str = "other", line_generator: BroadLineGenerator = None):
        self.match_id = match_id
        self.sport_name = sport_name.lower()
        self.lg = line_generator or BroadLineGenerator()

        # Live-протокол
        self.current_score_a = 0
        self.current_score_b = 0
        self.extra_stat_a = 0
        self.extra_stat_b = 0

        # Базовые коэффициенты силы
        self.strength_factor_a = 1.0
        self.strength_factor_b = 1.0

        # Momentum (динамика доминирования)
        self.momentum_factor = 0.0

    # ============================================================
    # LIVE STATE UPDATE
    # ============================================================

    def set_match_state(self, score_a: int, score_b: int, extra_a: int = 0, extra_b: int = 0) -> None:
        self.current_score_a = max(0, score_a)
        self.current_score_b = max(0, score_b)
        self.extra_stat_a = max(0, extra_a)
        self.extra_stat_b = max(0, extra_b)

    # ============================================================
    # MODEL SELECTION
    # ============================================================

    def _determine_best_model(self) -> str:
        """
        Выбор модели:
        - high_score_normal → волейбол, настольный теннис, бадминтон, киберспорт (фраги)
        - low_score_poisson → все остальные
        """
        high_score_keywords = ["volleyball", "table_tennis", "badminton", "cybersport_frags"]
        if any(s in self.sport_name for s in high_score_keywords):
            return "high_score_normal"
        return "low_score_poisson"

    # ============================================================
    # MAIN ANALYTICS LOOP
    # ============================================================

    def process_frame_data(self, tracking_data: Dict[str, Any], game_time_str: str, time_left_ratio: float) -> Dict[str, Any]:
        """
        Главный цикл обработки кадра для "Разных" видов спорта.
        """
        # -----------------------------
        # MOMENTUM MODEL
        # -----------------------------
        recent_dominance = float(tracking_data.get("recent_dominance_ratio", 0.5))
        recent_dominance = float(np.clip(recent_dominance, 0.05, 0.95))

        self.momentum_factor = (recent_dominance - 0.5) * 2.0

        # -----------------------------
        # LIVE STRENGTH MODEL
        # -----------------------------
        live_strength_a = self.strength_factor_a * (1.0 + self.momentum_factor * 0.15)
        live_strength_b = self.strength_factor_b * (1.0 - self.momentum_factor * 0.15)

        # -----------------------------
        # SUSPEND LOGIC
        # -----------------------------
        is_suspended = tracking_data.get("is_paused", False)

        # -----------------------------
        # MAIN MARKETS
        # -----------------------------
        model_type = self._determine_best_model()

        if model_type == "high_score_normal":
            # Высокосчётные виды спорта
            expected_total = float(tracking_data.get("expected_total_events", 100))
            expected_total = max(10.0, expected_total)

            base_markets = self.lg.calculate_high_score_line(
                pace=expected_total,
                efficiency_a=live_strength_a / (live_strength_a + live_strength_b),
                efficiency_b=live_strength_b / (live_strength_a + live_strength_b),
                time_left_ratio=time_left_ratio,
                current_score_a=self.current_score_a,
                current_score_b=self.current_score_b
            )
        else:
            # Низкосчётные виды спорта
            base_markets = self.lg.calculate_poisson_line(
                lambda_team_a=live_strength_a * 2.0,
                lambda_team_b=live_strength_b * 2.0,
                time_left_ratio=time_left_ratio,
                current_score_a=self.current_score_a,
                current_score_b=self.current_score_b
            )

        # -----------------------------
        # EXTRA STAT MARKETS
        # -----------------------------
        stat_lambda_a = float(tracking_data.get("base_stat_lambda_a", 1.5)) * live_strength_a
        stat_lambda_b = float(tracking_data.get("base_stat_lambda_b", 1.5)) * live_strength_b

        stat_markets = self.lg.calculate_poisson_line(
            lambda_team_a=stat_lambda_a,
            lambda_team_b=stat_lambda_b,
            time_left_ratio=time_left_ratio,
            current_score_a=self.extra_stat_a,
            current_score_b=self.extra_stat_b,
            max_goals_to_simulate=30
        )

        stat_name = tracking_data.get("extra_stat_name", "Statistic")

        active_specials = []
        for outcome in stat_markets.get("totals", []):
            active_specials.append({
                "market_name": outcome["market_name"]
                    .replace("TO", f"{stat_name} Total Over")
                    .replace("TU", f"{stat_name} Total Under"),
                "odds": outcome["odds"],
                "is_suspended": is_suspended or outcome.get("is_suspended", False)
            })

        # -----------------------------
        # SUSPEND MAIN MARKETS
        # -----------------------------
        if is_suspended:
            for m in base_markets.get("main_outcomes", []):
                m["is_suspended"] = True
            for t in base_markets.get("totals", []):
                t["is_suspended"] = True

        # -----------------------------
        # POSSESSION MODEL
        # -----------------------------
        possession_a = round(max(min(recent_dominance * 100.0, 95.0), 5.0), 1)
        possession_b = round(100.0 - possession_a, 1)

        # -----------------------------
        # FINAL OUTPUT PACKAGE
        # -----------------------------
        return {
            "match_id": self.match_id,
            "sport": self.sport_name,
            "game_time": game_time_str,

            "ball_state": {
                "x": float(tracking_data.get("object_x", 0.0)),
                "y": float(tracking_data.get("object_y", 0.0)),
                "vx": float(self.momentum_factor),
                "vy": 0.0,
                "last_touch_id": tracking_data.get("last_active_player_id", -1)
            },

            "metrics": {
                "possession_a": possession_a,
                "possession_b": possession_b,
                "xg_a": float(tracking_data.get("performance_index_a", 0.0)),
                "xg_b": float(tracking_data.get("performance_index_b", 0.0)),
                "dangerous_attacks_a": int(tracking_data.get("attacks_count_a", 0)),
                "dangerous_attacks_b": int(tracking_data.get("attacks_count_b", 0))
            },

            "line_data": {
                "main_outcomes": base_markets.get("main_outcomes", []),
                "totals": base_markets.get("totals", []),
                "handicaps": [],
                "active_specials": active_specials
            }
        }
