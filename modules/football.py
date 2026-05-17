# ============================================
# Prizolov Sports AI - Football Analytics Module
# Version: 3.02 (Absolute Deployment Refactoring)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at prizolov.ru
# ============================================

import numpy as np
from typing import Dict, Any, List, Tuple

try:
    from core.line_generator import BroadLineGenerator
except ModuleNotFoundError:
    from prizolov_sports_ai.core.line_generator import BroadLineGenerator

class FootballAnalyticsModule:
    """Профильный модуль ИИ-аналитики и генерации широкой линии для футбола"""

    def __init__(self, match_id: str, line_generator: BroadLineGenerator):
        self.match_id = match_id
        self.lg = line_generator
        
        # Размеры стандартного поля FIFA (в метрах)
        self.pitch_length = 105.0
        self.pitch_width = 68.0
        
        # Инициализация Live-метрик матча
        self.current_score_a = 0
        self.current_score_b = 0
        self.corners_a = 0
        self.corners_b = 0
        
        # Базовая атакующая интенсивность команд (лямбды для Пуассона)
        self.base_lambda_a = 1.2
        self.base_lambda_b = 1.0
        
        # Накопительные счетчики владения
        self.possession_frames_a = 0
        self.possession_frames_b = 0

    def set_match_state(self, score_a: int, score_b: int, corners_a: int, corners_b: int) -> None:
        """Обновление официального протокола матча"""
        self.current_score_a = score_a
        self.current_score_b = score_b
        self.corners_a = corners_a
        self.corners_b = corners_b

    def calculate_homography_coords(self, pixel_coords: Tuple[float, float], h_matrix: np.ndarray) -> Tuple[float, float]:
        """Превращает пиксельные координаты экрана в метрические координаты поля"""
        if h_matrix is None:
            return pixel_coords
        point = np.array([pixel_coords, pixel_coords, 1.0])
        transformed = np.dot(h_matrix, point)
        if transformed == 0:
            return pixel_coords
        real_x = transformed / transformed
        real_y = transformed / transformed
        return (float(real_x), float(real_y))

    def evaluate_offside(self, 
                         defenders_metric: List[float], 
                         attackers_metric: List[float], 
                         ball_metric_x: float, 
                         is_pass_event: bool) -> Tuple[bool, List[int]]:
        """Фиксация офсайдного положения в метрической системе координат"""
        if not is_pass_event or len(defenders_metric) < 2:
            return False, []

        sorted_defenders = sorted(defenders_metric, reverse=True)
        offside_line = sorted_defenders

        offside_players = []
        for player_id, act_x in attackers_metric:
            if act_x > offside_line and act_x > ball_metric_x:
                offside_players.append(player_id)

        return len(offside_players) > 0, offside_players

    def process_frame_data(self, 
                           tracking_data: Dict[str, Any], 
                           game_time_str: str, 
                           time_left_ratio: float) -> Dict[str, Any]:
        """Главный цикл обработки кадра. Рассчитывает Live-статистику и формирует линию"""
        ball_owner_team = tracking_data.get("ball_owner_team", None)
        if ball_owner_team == "A":
            self.possession_frames_a += 1
        elif ball_owner_team == "B":
            self.possession_frames_b += 1

        total_p_frames = self.possession_frames_a + self.possession_frames_b
        p_pct_a = 50.0
        p_pct_b = 50.0
        if total_p_frames > 0:
            p_pct_a = round((self.possession_frames_a / total_p_frames) * 100, 1)
            p_pct_b = round(100.0 - p_pct_a, 1)

        danger_attacks_a = tracking_data.get("danger_attacks_a", 0)
        danger_attacks_b = tracking_data.get("danger_attacks_b", 0)
        
        live_lambda_a = self.base_lambda_a * (p_pct_a / 50.0) + (danger_attacks_a * 0.1)
        live_lambda_b = self.base_lambda_b * (p_pct_b / 50.0) + (danger_attacks_b * 0.1)

        # Расчет основных рынков
        base_markets = self.lg.calculate_poisson_line(
            lambda_team_a=live_lambda_a,
            lambda_team_b=live_lambda_b,
            time_left_ratio=time_left_ratio,
            current_score_a=self.current_score_a,
            current_score_b=self.current_score_b
        )

        # Расчет угловых
        lambda_corners_a = 5.0 * (live_lambda_a / max(self.base_lambda_a, 0.1))
        lambda_corners_b = 4.5 * (live_lambda_b / max(self.base_lambda_b, 0.1))
        
        corners_markets = self.lg.calculate_poisson_line(
            lambda_team_a=lambda_corners_a,
            lambda_team_b=lambda_corners_b,
            time_left_ratio=time_left_ratio,
            current_score_a=self.corners_a,
            current_score_b=self.corners_b
        )
        
        active_specials = []
        for outcome in corners_markets["main_outcomes"]:
            m_name = outcome["market_name"].replace("1", "Corners Team A").replace("X", "Corners Draw").replace("2", "Corners Team B")
            active_specials.append({"market_name": m_name, "odds": outcome["odds"], "is_suspended": outcome["is_suspended"]})
            
        for outcome in corners_markets["totals"]:
            m_name = outcome["market_name"].replace("TO", "Corners Total Over").replace("TU", "Corners Total Under")
            active_specials.append({"market_name": m_name, "odds": outcome["odds"], "is_suspended": outcome["is_suspended"]})

        output_package = {
            "match_id": self.match_id,
            "sport": "football",
            "game_time": game_time_str,
            "ball_state": {
                "x": tracking_data.get("ball_x", 0.0),
                "y": tracking_data.get("ball_y", 0.0),
                "vx": tracking_data.get("ball_vx", 0.0),
                "vy": tracking_data.get("ball_vy", 0.0),
                "last_touch_id": tracking_data.get("last_touch_id", -1)
            },
            "metrics": {
                "possession_a": p_pct_a,
                "possession_b": p_pct_b,
                "xg_a": tracking_data.get("live_xg_a", 0.0),
                "xg_b": tracking_data.get("live_xg_b", 0.0),
                "dangerous_attacks_a": danger_attacks_a,
                "dangerous_attacks_b": danger_attacks_b
            },
            "line_data": {
                "main_outcomes": base_markets["main_outcomes"],
                "totals": base_markets["totals"],
                "handicaps": [],
                "active_specials": active_specials
            }
        }

        return output_package
