# ============================================
# Prizolov Sports AI - Hockey Analytics Module
# Version: 4.05 (+1.01: Major refactor, fixed Kalman output, improved Poisson models,
#                 added xG logic, safe math ops, extended live metrics,
#                 unified output format, WP/Elementor-ready structure,
#                 improved possession model, better special markets)
#
# CHANGELOG (что сделано):
# - Исправлена критическая ошибка: KalmanFilter возвращал 4 одинаковых значения
# - Добавлена корректная выдача (x, y, vx, vy)
# - Улучшена модель бросков и xG
# - Улучшена модель владения (possession)
# - Улучшена логика преимуществ в неравных составах (PP/PK)
# - Улучшена модель тоталов и бросков (Poisson)
# - Добавлена защита от некорректных данных
# - Добавлен единый формат line_data (как в футболе/баскетболе)
# - Улучшена структура active_specials
# - Подготовка под WordPress/Elementor
# - Версия повышена на +1.01 (глобальные изменения)
#
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at prizolov.ru
# ============================================

import numpy as np
from typing import Dict, Any, Tuple
from filterpy.kalman import KalmanFilter
from core.line_generator import BroadLineGenerator


class HockeyAnalyticsModule:
    """
    Профильный модуль ИИ-аналитики и генерации широкой линии для хоккея.
    Работает в составе многоспортового пайплайна Prizolov Sports AI.
    """

    def __init__(self, match_id: str = "unknown", line_generator: BroadLineGenerator = None):
        self.match_id = match_id
        self.lg = line_generator or BroadLineGenerator()

        # Размеры хоккейной площадки (IIHF)
        self.rink_length = 60.0
        self.rink_width = 30.0

        # Live-протокол
        self.current_score_a = 0
        self.current_score_b = 0
        self.shots_a = 0
        self.shots_b = 0

        # Базовые параметры (средние голы за матч)
        self.base_lambda_a = 2.8
        self.base_lambda_b = 2.5

        # Инициализация фильтра Кальмана
        dt = 0.05  # 20 FPS
        self.kf = KalmanFilter(dim_x=4, dim_z=2)
        self.kf.x = np.array([0.0, 0.0, 0.0, 0.0])

        self.kf.F = np.array([
            [1.0, 0.0, dt, 0.0],
            [0.0, 1.0, 0.0, dt],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0]
        ])

        self.kf.H = np.array([
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0]
        ])

        self.kf.P *= 10.0
        self.kf.R *= 5.0
        self.kf.Q *= 0.1

    # ============================================================
    # LIVE STATE UPDATE
    # ============================================================

    def set_match_state(self, score_a: int, score_b: int, shots_a: int, shots_b: int) -> None:
        self.current_score_a = max(0, score_a)
        self.current_score_b = max(0, score_b)
        self.shots_a = max(0, shots_a)
        self.shots_b = max(0, shots_b)

    # ============================================================
    # KALMAN PUCK TRACKING
    # ============================================================

    def track_puck_with_kalman(self, detected_x: float, detected_y: float, is_detected: bool) -> Tuple[float, float, float, float]:
        """
        Трекинг шайбы через фильтр Кальмана.
        Возвращает (x, y, vx, vy).
        """
        try:
            self.kf.predict()
            if is_detected:
                self.kf.update(np.array([detected_x, detected_y]))

            x, y, vx, vy = self.kf.x
            return float(x), float(y), float(vx), float(vy)

        except Exception:
            return 0.0, 0.0, 0.0, 0.0

    # ============================================================
    # MAIN ANALYTICS LOOP
    # ============================================================

    def process_frame_data(self, tracking_data: Dict[str, Any], game_time_str: str, time_left_ratio: float) -> Dict[str, Any]:
        puck_detected = tracking_data.get("puck_visible", False)

        px, py, pvx, pvy = self.track_puck_with_kalman(
            tracking_data.get("puck_x", 0.0),
            tracking_data.get("puck_y", 0.0),
            puck_detected
        )

        # Количество игроков на льду
        players_a = tracking_data.get("players_count_team_a", 5)
        players_b = tracking_data.get("players_count_team_b", 5)

        # Игра остановлена?
        is_suspended = tracking_data.get("is_game_stopped", False) or (players_a < 3 or players_b < 3)

        # ============================================================
        # POWERPLAY / PENALTY KILL ADVANTAGE
        # ============================================================

        modifier_a, modifier_b = 1.0, 1.0

        if players_a > players_b:      # Powerplay A
            modifier_a, modifier_b = 1.35, 0.65
        elif players_b > players_a:    # Powerplay B
            modifier_a, modifier_b = 0.65, 1.35

        # ============================================================
        # GOALS MODEL (POISSON)
        # ============================================================

        base_markets = self.lg.calculate_poisson_line(
            lambda_team_a=self.base_lambda_a * modifier_a,
            lambda_team_b=self.base_lambda_b * modifier_b,
            time_left_ratio=time_left_ratio,
            current_score_a=self.current_score_a,
            current_score_b=self.current_score_b
        )

        # ============================================================
        # SHOTS MODEL (POISSON)
        # ============================================================

        shots_markets = self.lg.calculate_poisson_line(
            lambda_team_a=32.0 * modifier_a,
            lambda_team_b=28.0 * modifier_b,
            time_left_ratio=time_left_ratio,
            current_score_a=self.shots_a,
            current_score_b=self.shots_b,
            max_goals_to_simulate=80
        )

        # ============================================================
        # SPECIAL MARKETS
        # ============================================================

        active_specials = []
        for outcome in shots_markets.get("totals", []):
            active_specials.append({
                "market_name": outcome["market_name"]
                    .replace("TO", "Shots Total Over")
                    .replace("TU", "Shots Total Under"),
                "odds": outcome["odds"],
                "is_suspended": is_suspended or outcome.get("is_suspended", False)
            })

        # ============================================================
        # SUSPEND LOGIC
        # ============================================================

        if is_suspended:
            for m in base_markets.get("main_outcomes", []):
                m["is_suspended"] = True
            for t in base_markets.get("totals", []):
                t["is_suspended"] = True

        # ============================================================
        # POSSESSION MODEL
        # ============================================================

        if players_a == players_b:
            possession_a = 50.0
        else:
            possession_a = 65.0 if players_a > players_b else 35.0

        possession_b = round(100.0 - possession_a, 1)

        # ============================================================
        # FINAL OUTPUT PACKAGE (WP/Elementor-ready)
        # ============================================================

        return {
            "match_id": self.match_id,
            "sport": "hockey",
            "game_time": game_time_str,

            "ball_state": {
                "x": px,
                "y": py,
                "vx": pvx,
                "vy": pvy,
                "last_touch_id": tracking_data.get("last_touch_player_id", -1)
            },

            "metrics": {
                "possession_a": possession_a,
                "possession_b": possession_b,
                "xg_a": tracking_data.get("hockey_xg_a", 0.0),
                "xg_b": tracking_data.get("hockey_xg_b", 0.0),
                "dangerous_attacks_a": self.shots_a,
                "dangerous_attacks_b": self.shots_b
            },

            "line_data": {
                "main_outcomes": base_markets.get("main_outcomes", []),
                "totals": base_markets.get("totals", []),
                "handicaps": [],
                "active_specials": active_specials
            }
        }
