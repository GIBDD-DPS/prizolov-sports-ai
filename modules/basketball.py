# ============================================
# Prizolov Sports AI - Basketball Analytics Module
# Version: 4.03 (+1.01: Major refactor, stability fixes, safe math ops,
#                 extended live metrics, unified output format,
#                 improved pace model, foul-impact tuning,
#                 added description block, WP/Elementor-ready structure)
#
# CHANGELOG (что сделано):
# - Полная переработка структуры модуля под многоспортовый пайплайн
# - Добавлена защита от деления на ноль и некорректных данных
# - Улучшена модель Live Pace (ограничения, стабилизация)
# - Улучшена модель эффективности (live_eff_a / live_eff_b)
# - Добавлен расширенный пакет метрик для сайта (WP/Elementor)
# - Добавлена нормализация владений и xShot
# - Улучшена логика фолов и бонусов
# - Добавлен fail-safe для трекинга мяча
# - Добавлен единый формат line_data (совместим с football/hockey)
# - Версия повышена на +1.01 (глобальные изменения)
#
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at prizolov.ru
# ============================================

import numpy as np
from typing import Dict, Any, List, Tuple
from core.line_generator import BroadLineGenerator


class BasketballAnalyticsModule:
    """
    Профильный модуль ИИ-аналитики и генерации широкой линии для баскетбола.
    Работает в составе многоспортового пайплайна Prizolov Sports AI.
    """

    def __init__(self, match_id: str = "unknown", line_generator: BroadLineGenerator = None):
        self.match_id = match_id
        self.lg = line_generator or BroadLineGenerator()

        # Размеры стандартной площадки FIBA (в метрах)
        self.court_length = 28.0
        self.court_width = 15.0

        # Live-протокол
        self.current_score_a = 0
        self.current_score_b = 0
        self.fouls_a = 0
        self.fouls_b = 0

        # Базовые параметры матча
        self.base_pace = 75.0
        self.base_efficiency_a = 1.05
        self.base_efficiency_b = 1.02

        # Накопительные данные
        self.total_possessions_observed = 0
        self.seconds_elapsed = 1

    # ============================================================
    # LIVE STATE UPDATE
    # ============================================================

    def set_match_state(self, score_a: int, score_b: int, fouls_a: int, fouls_b: int) -> None:
        """Обновление официального live-протокола (счет, командные фолы)."""
        self.current_score_a = max(0, score_a)
        self.current_score_b = max(0, score_b)
        self.fouls_a = max(0, fouls_a)
        self.fouls_b = max(0, fouls_b)

    # ============================================================
    # BALL TRACKING
    # ============================================================

    def analyze_ball_trajectory_3d(
        self,
        coords_2d: Tuple[float, float],
        ball_bounding_box_size: float,
        camera_factor: float
    ) -> float:
        """
        Рассчитывает условную координату Z (высоту полета мяча).
        """
        if ball_bounding_box_size <= 0:
            return 0.0
        try:
            estimated_z = (1.0 / ball_bounding_box_size) * camera_factor
            return float(max(0.0, estimated_z))
        except Exception:
            return 0.0

    # ============================================================
    # MAIN ANALYTICS LOOP
    # ============================================================

    def process_frame_data(
        self,
        tracking_data: Dict[str, Any],
        game_time_str: str,
        time_left_ratio: float,
        elapsed_seconds: int
    ) -> Dict[str, Any]:
        """
        Главный цикл обработки баскетбольного кадра.
        """
        self.seconds_elapsed = max(1, elapsed_seconds)

        # -----------------------------
        # LIVE PACE MODEL
        # -----------------------------
        detected_possessions = tracking_data.get("cumulative_possessions", 0)
        if detected_possessions > 0:
            self.total_possessions_observed = detected_possessions
            live_pace = (self.total_possessions_observed / self.seconds_elapsed) * 2400.0
            live_pace = float(np.clip(live_pace, 60.0, 110.0))
        else:
            live_pace = self.base_pace

        # -----------------------------
        # LIVE EFFICIENCY MODEL
        # -----------------------------
        xshot_a = float(tracking_data.get("recent_xshot_avg_a", 0.45))
        xshot_b = float(tracking_data.get("recent_xshot_avg_b", 0.43))

        xshot_a = float(np.clip(xshot_a, 0.30, 0.70))
        xshot_b = float(np.clip(xshot_b, 0.30, 0.70))

        live_eff_a = self.base_efficiency_a * (xshot_a / 0.45)
        live_eff_b = self.base_efficiency_b * (xshot_b / 0.43)

        # -----------------------------
        # FOUL IMPACT
        # -----------------------------
        is_free_throw = tracking_data.get("is_free_throw_active", False)
        is_suspended = tracking_data.get("is_timeout_active", False) or is_free_throw

        if self.fouls_a > 4:
            live_eff_b += 0.08
        if self.fouls_b > 4:
            live_eff_a += 0.08

        # -----------------------------
        # MAIN MARKETS (TOTALS / OUTCOMES)
        # -----------------------------
        base_markets = self.lg.calculate_high_score_line(
            pace=live_pace,
            efficiency_a=live_eff_a,
            efficiency_b=live_eff_b,
            time_left_ratio=time_left_ratio,
            current_score_a=self.current_score_a,
            current_score_b=self.current_score_b
        )

        # -----------------------------
        # FOUL MARKETS (POISSON)
        # -----------------------------
        lambda_fouls_a = 4.0 * (live_pace / self.base_pace)
        lambda_fouls_b = 4.2 * (live_pace / self.base_pace)

        fouls_markets = self.lg.calculate_poisson_line(
            lambda_team_a=lambda_fouls_a,
            lambda_team_b=lambda_fouls_b,
            time_left_ratio=time_left_ratio,
            current_score_a=self.fouls_a,
            current_score_b=self.fouls_b
        )

        active_specials = []
        for outcome in fouls_markets.get("totals", []):
            m_name = outcome["market_name"].replace("TO", "Fouls Total Over").replace("TU", "Fouls Total Under")
            active_specials.append({
                "market_name": m_name,
                "odds": outcome["odds"],
                "is_suspended": is_suspended or outcome.get("is_suspended", False)
            })

        # -----------------------------
        # SUSPEND LOGIC
        # -----------------------------
        if is_suspended:
            for m in base_markets.get("main_outcomes", []):
                m["is_suspended"] = True
            for t in base_markets.get("totals", []):
                t["is_suspended"] = True

        # -----------------------------
        # BALL TRACKING
        # -----------------------------
        raw_bx = float(tracking_data.get("ball_x", 0.0))
        raw_by = float(tracking_data.get("ball_y", 0.0))
        bbox_w = float(tracking_data.get("ball_bbox_width", 0.05))

        bz = self.analyze_ball_trajectory_3d(
            (raw_bx, raw_by),
            bbox_w,
            camera_factor=1.5
        )

        # ============================================================
        # FINAL OUTPUT PACKAGE (WP/Elementor-ready)
        # ============================================================

        output_package = {
            "match_id": self.match_id,
            "sport": "basketball",
            "game_time": game_time_str,

            "ball_state": {
                "x": raw_bx,
                "y": raw_by,
                "vx": bz,
                "vy": float(tracking_data.get("ball_vy", 0.0)),
                "last_touch_id": tracking_data.get("last_touch_player_id", -1)
            },

            "metrics": {
                "possession_a": float(tracking_data.get("live_possession_pct_a", 50.0)),
                "possession_b": 0.0,
                "xg_a": xshot_a,
                "xg_b": xshot_b,
                "dangerous_attacks_a": tracking_data.get("paint_entries_a", 0),
                "dangerous_attacks_b": tracking_data.get("paint_entries_b", 0)
            },

            "line_data": {
                "main_outcomes": base_markets.get("main_outcomes", []),
                "totals": base_markets.get("totals", []),
                "handicaps": [],
                "active_specials": active_specials
            }
        }

        # Нормализация владений
        output_package["metrics"]["possession_b"] = round(
            100.0 - output_package["metrics"]["possession_a"], 1
        )

        return output_package
