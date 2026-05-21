# ============================================
# Prizolov Sports AI - Basketball Analytics Module
# Version: 3.02 (Syntax & Flat-Cloud Imports Fix)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at prizolov.ru
# ============================================

import numpy as np
from typing import Dict, Any, List, Tuple
from core.line_generator import BroadLineGenerator

class BasketballAnalyticsModule:
    """Профильный модуль ИИ-аналитики и генерации широкой линии для баскетбола"""

    def __init__(self, match_id: str, line_generator: BroadLineGenerator):
        self.match_id = match_id
        self.lg = line_generator
        
        # Размеры стандартной площадки FIBA (в метрах)
        self.court_length = 28.0
        self.court_width = 15.0
        
        # Официальный Live-протокол матча
        self.current_score_a = 0
        self.current_score_b = 0
        self.fouls_a = 0
        self.fouls_b = 0
        
        # Базовые параметры баскетбольного матча (на 40 минут игры FIBA)
        self.base_pace = 75.0          # Среднее количество владений каждой команды за матч
        self.base_efficiency_a = 1.05  # Очков за одно владение команды А (105 ORTG)
        self.base_efficiency_b = 1.02  # Очков за одно владение команды Б (102 ORTG)
        
        # Накопительные данные для расчета Live Pace
        self.total_possessions_observed = 0
        self.seconds_elapsed = 0

    def set_match_state(self, score_a: int, score_b: int, fouls_a: int, fouls_b: int) -> None:
        """Обновление официального live-протокола (счет, командные фолы)"""
        self.current_score_a = score_a
        self.current_score_b = score_b
        self.fouls_a = fouls_a
        self.fouls_b = fouls_b

    def analyze_ball_trajectory_3d(self, 
                                   coords_2d: Tuple[float, float], 
                                   ball_bounding_box_size: float, 
                                   camera_factor: float) -> float:
        """
        Рассчитывает условную координату Z (высоту полета мяча).
        """
        if ball_bounding_box_size <= 0:
            return 0.0
        estimated_z = (1.0 / ball_bounding_box_size) * camera_factor
        return float(estimated_z)

    def process_frame_data(self, 
                           tracking_data: Dict[str, Any], 
                           game_time_str: str, 
                           time_left_ratio: float,
                           elapsed_seconds: int) -> Dict[str, Any]:
        """
        Главный цикл обработки баскетбольного кадра.
        """
        self.seconds_elapsed = max(elapsed_seconds, 1)
        
        # Исправлено: Закрыта строковая кавычка для Amvera Cloud
        detected_possessions = tracking_data.get("cumulative_possessions", 0)
        if detected_possessions > 0:
            self.total_possessions_observed = detected_possessions
            live_pace = (self.total_possessions_observed / self.seconds_elapsed) * 2400.0
            live_pace = max(min(live_pace, 110.0), 60.0)
        else:
            live_pace = self.base_pace

        xshot_a = tracking_data.get("recent_xshot_avg_a", 0.45)
        xshot_b = tracking_data.get("recent_xshot_avg_b", 0.43)
        
        live_eff_a = self.base_efficiency_a * (xshot_a / 0.45)
        live_eff_b = self.base_efficiency_b * (xshot_b / 0.43)

        is_free_throw = tracking_data.get("is_free_throw_active", False)
        is_suspended = tracking_data.get("is_timeout_active", False) or is_free_throw
        
        if self.fouls_a > 4: live_eff_b += 0.08
        if self.fouls_b > 4: live_eff_a += 0.08

        base_markets = self.lg.calculate_high_score_line(
            pace=live_pace,
            efficiency_a=live_eff_a,
            efficiency_b=live_eff_b,
            time_left_ratio=time_left_ratio,
            current_score_a=self.current_score_a,
            current_score_b=self.current_score_b
        )

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
        for outcome in fouls_markets["totals"]:
            m_name = outcome["market_name"].replace("TO", "Fouls Total Over").replace("TU", "Fouls Total Under")
            active_specials.append({
                "market_name": m_name,
                "odds": outcome["odds"],
                "is_suspended": is_suspended or outcome["is_suspended"]
            })

        if is_suspended:
            for m in base_markets["main_outcomes"]: m["is_suspended"] = True
            for t in base_markets["totals"]: t["is_suspended"] = True

        raw_bx = tracking_data.get("ball_x", 0.0)
        raw_by = tracking_data.get("ball_y", 0.0)
        bbox_w = tracking_data.get("ball_bbox_width", 0.05)
        bz = self.analyze_ball_trajectory_3d((raw_bx, raw_by), bbox_w, camera_factor=1.5)

        output_package = {
            "match_id": self.match_id,
            "sport": "basketball",
            "game_time": game_time_str,
            "ball_state": {
                "x": raw_bx,
                "y": raw_by,
                "vx": bz,
                "vy": tracking_data.get("ball_vy", 0.0),
                "last_touch_id": tracking_data.get("last_touch_player_id", -1)
            },
            "metrics": {
                "possession_a": tracking_data.get("live_possession_pct_a", 50.0),
                "possession_b": 0.0,
                "xg_a": xshot_a,
                "xg_b": xshot_b,
                "dangerous_attacks_a": tracking_data.get("paint_entries_a", 0),
                "dangerous_attacks_b": tracking_data.get("paint_entries_b", 0)
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
