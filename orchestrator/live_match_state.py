# ============================================
# Prizolov Sports AI - Live Match Orchestrator
# Version: 1.00 (Production Integration Layer)
#
# CHANGELOG:
# 1.00:
# - Создан единый live-state orchestrator
# - Интеграция всех core-модулей в единый объект
# - Поддержка live-обновления 20–30 FPS
# - Подготовка под API / WordPress Elementor
#
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Real-time match state aggregation
# ============================================

import time
from typing import Dict, Any, Optional

from core.radar_renderer import SportsRadarRenderer
from core.trend_predictor import MicroTrendPredictor
from core.weather_analytics import WeatherAnalyticsEngine
from core.referee_analytics import RefereeSeverityAnalytics
from core.risk_manager import RiskManagementEngine
from core.stream_validator import StreamQualityValidator


class LiveMatchState:
    """
    Единый live-state агрегатор.
    Собирает данные из всех модулей ядра и формирует готовый JSON-объект.
    """

    def __init__(self, match_id: str):
        self.match_id = match_id

        # Подключаем модули ядра
        self.radar = SportsRadarRenderer("football")
        self.trends = MicroTrendPredictor()
        self.weather = WeatherAnalyticsEngine()
        self.referee = RefereeSeverityAnalytics()
        self.risk = RiskManagementEngine()
        self.stream = StreamQualityValidator()

        # Live-поля
        self.score = "0:0"
        self.time_seconds = 0
        self.last_update_ts = time.time()

        # Данные CV (обновляются извне)
        self.ball_state = {"x": 50.0, "y": 34.0}
        self.team_a_players = []
        self.team_b_players = []

        # Прогнозы и линия (обновляются извне)
        self.predictions = {"main": [], "totals": [], "handicaps": []}
        self.line = {"main_outcomes": [], "totals": [], "handicaps": []}

    # ============================================================
    # Методы обновления live-данных (вызываются CV/AI-пайплайном)
    # ============================================================

    def update_score(self, score: str):
        self.score = score

    def update_time(self, seconds: int):
        self.time_seconds = seconds

    def update_ball(self, x: float, y: float):
        self.ball_state = {"x": x, "y": y}

    def update_players(self, team_a: list, team_b: list):
        self.team_a_players = team_a
        self.team_b_players = team_b

    def update_predictions(self, predictions: Dict[str, Any]):
        self.predictions = predictions

    def update_line(self, line: Dict[str, Any]):
        self.line = line

    # ============================================================
    # Основной метод: сборка единого JSON-объекта
    # ============================================================

    def build_state(self) -> Dict[str, Any]:
        """
        Собирает полный live-state матча.
        Вызывается API-слоем при каждом запросе.
        """

        # 1. Радар
        radar_svg = self.radar.render_svg_frame(
            ball_x=self.ball_state["x"],
            ball_y=self.ball_state["y"],
            team_a_players=self.team_a_players,
            team_b_players=self.team_b_players
        )

        # 2. Тренды
        pressure_a, pressure_b = self.trends.predict_next_interval_pressure()

        # 3. Погода
        decay_a, decay_b = self.weather.calculate_weather_decay_modifiers()

        # 4. Судья
        calibrated_lambda = self.referee.calibrate_discipline_intensity(0.25)

        # 5. Риск
        current_margin = self.risk.adjust_margin_by_volatility(
            live_xg_speed=0.12,
            is_critical_moment=False
        )

        # 6. Стрим
        is_stream_broken = self.stream.is_stream_broken

        # 7. Финальный JSON
        return {
            "match_id": self.match_id,
            "teams": {
                "home": "ЦСКА (Москва)",
                "away": "Динамо (Москва)"
            },
            "score": self.score,
            "time_seconds": self.time_seconds,

            "radar_svg": radar_svg,

            "predictions": self.predictions,
            "line": self.line,

            "trends": {
                "pressure_a": pressure_a,
                "pressure_b": pressure_b
            },

            "weather": {
                "condition": self.weather.current_weather_condition,
                "decay_a": decay_a,
                "decay_b": decay_b,
                "wind_speed_mps": self.weather.wind_speed_mps,
                "temperature_c": self.weather.temperature_c
            },

            "referee": {
                "name": self.referee.referee_name,
                "severity_index": self.referee.severity_index,
                "discipline_lambda": calibrated_lambda
            },

            "risk": {
                "current_margin": current_margin
            },

            "stream": {
                "is_stream_broken": is_stream_broken
            }
        }
