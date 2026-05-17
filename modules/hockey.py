# ============================================
# Prizolov Sports AI - Hockey Analytics Module
# Version: 3.02 (Absolute Deployment Refactoring)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at prizolov.ru
# ============================================

import numpy as np
from typing import Dict, Any, List, Tuple
from filterpy.kalman import KalmanFilter

try:
    from core.line_generator import BroadLineGenerator
except ModuleNotFoundError:
    from prizolov_sports_ai.core.line_generator import BroadLineGenerator

class HockeyAnalyticsModule:
    """Профильный модуль ИИ-аналитики и генерации широкой линии для хоккея"""

    def __init__(self, match_id: str, line_generator: BroadLineGenerator):
        self.match_id = match_id
        self.lg = line_generator
        
        self.rink_length = 60.0
        self.rink_width = 30.0
        
        self.current_score_a = 0
        self.current_score_b = 0
        self.shots_a = 0
        self.shots_b = 0
        
        self.base_lambda_a = 2.8
        self.base_lambda_b = 2.5
        
        self.kf = KalmanFilter(dim_x=4, dim_z=2)
        self.kf.x = np.array([0.0, 0.0, 0.0, 0.0])
        self.kf.F = np.array([[1, 0, 1, 0], [0, 1, 0, 1], [0, 0, 1, 0], [0, 0, 0, 1]])
        self.kf.H = np.array([[1, 0, 0, 0], [0, 1, 0, 0]])
        self.kf.P *= 10.0
        self.kf.R *= 5.0
        self.kf.Q *= 0.1

    def set_match_state(self, score_a: int, score_b: int, shots_a: int, shots_b: int) -> None:
        """Обновление официального live-протокола игры"""
        self.current_score_a = score_a
        self.current_score_b = score_b
        self.shots_a = shots_a
        self.shots_b = shots_b

    def track_puck_with_kalman(self, detected_x: float, detected_y: float, is_detected: bool) -> Tuple[float, float, float, float]:
        """Прогнозирует или обновляет положение шайбы с помощью фильтра Кальмана"""
        self.kf.predict()
        if is_detected:
            self.kf.update(np.array([detected_x, detected_y]))
        return float(self.kf.x[0]), float(self.kf.x[1]), float(self.kf.x[2]), float(self.kf.x[3])

    def process_frame_data(self, 
                           tracking_data: Dict[str, Any], 
                           game_time_str: str, 
                           time_left_ratio: float) -> Dict[str, Any]:
        """Главный цикл обработки хоккейного кадра"""
        puck_detected = tracking_data.get("puck_visible", False)
        raw_px = tracking_data.get("puck_x", 0.0)
        raw_py = tracking_data.get("puck_y", 0.0)
        
        px, py, pvx, pvy = self.track_puck_with_kalman(raw_px, raw_py, puck_detected)

        players_on_ice_a = tracking_data.get("players_count_team_a", 5)
        players_on_ice_b = tracking_data.get("players_count_team_b", 5)
        
        is_suspended = tracking_data.get("is_game_stopped", False) or (players_on_ice_a < 3 or players_on_ice_b < 3)

        modifier_a = 1.0
        modifier_b = 1.0
        if players_on_ice_a > players_on_ice_b:
            modifier_a = 1.4
            modifier_b = 0.6
        elif players_on_ice_b > players_on_ice_a:
            modifier_a = 0.6
            modifier_b = 1.4

        live_lambda_a = self.base_lambda_a * modifier_a
        live_lambda_b = self.base_lambda_b * modifier_b

        base_markets = self.lg.calculate_poisson_line(
            lambda_team_a=live_lambda_a,
            lambda_team_b=live_lambda_b,
            time_left_ratio=time_left_ratio,
            current_score_a=self.current_score_a,
            current_score_b=self.current_score_b
        )

        lambda_shots_a = 32.0 * (live_lambda_a / self.base_lambda_a)
        lambda_shots_b = 28.0 * (live_lambda_b / self.base_lambda_b)
        
        shots_markets = self.lg.calculate_poisson_line(
            lambda_team_a=lambda_shots_a,
            lambda_team_b=lambda_shots_b,
            time_left_ratio=time_left_ratio,
            current_score_a=self.shots_a,
            current_score_b=self.shots_b,
            max_goals_to_simulate=80
        )

        active_specials = []
        for outcome in shots_markets["totals"]:
            m_name = outcome["market_name"].replace("TO", "Shots Total Over").replace("TU", "Shots Total Under")
            active_specials.append({
                "market_name": m_name, 
                "odds": outcome["odds"], 
                "is_suspended": is_suspended or outcome["is_suspended"]
            })

        if is_suspended:
            for m in base_markets["main_outcomes"]: m["is_suspended"] = True
            for t in base_markets["totals"]: t["is_suspended"] = True

        output_package = {
            "match_id": self.match_id,
            "sport": "hockey",
            "game_time": game_time_str,
            "ball_state": {
                "x": px, "y": py, "vx": pvx, "vy": pvy,
                "last_touch_id": tracking_data.get("last_touch_player_id", -1)
            },
            "metrics": {
                "possession_a": 50.0 if players_on_ice_a == players_on_ice_b else (65.0 if players_on_ice_a > players_on_ice_b else 35.0),
                "possession_b": 0.0,
                "xg_a": tracking_data.get("hockey_xg_a", 0.0),
                "hockey_xg_b": tracking_data.get("hockey_xg_b", 0.0),
                "dangerous_attacks_a": self.shots_a,
                "dangerous_attacks_b": self.shots_b
            },
            "line_data": {
                "main_outcomes": base_markets["main_outcomes"],
                "totals": base_markets["totals"],
                "handicaps": [],
                "active_specials": active_specials
            }
        }

        output_package["metrics"]["possession_b"] = round(100.0 - output_package["metrics"]["possession_a"], 1)
        return output_package
