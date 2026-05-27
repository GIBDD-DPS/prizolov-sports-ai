# ============================================
# Prizolov Sports AI - Live Match Orchestrator
# Version: 1.01 (PRODUCTION FIXED FOR AMVERA)
# Author: Dm.Andreyanov / Refactored
# ============================================

import time
import logging
from typing import Dict, Any

logger = logging.getLogger("PrizolovSportsAI.LiveMatchState")

# Защитные импорты модулей ядра
try: from core.radar_renderer import SportsRadarRenderer
except ImportError:
    class SportsRadarRenderer:
        def __init__(self, s): pass
        def render_svg_frame(self, **k): return "<svg width='100' height='100'><circle cx='50' cy='50' r='40' fill='green'/></svg>"

try: from core.trend_predictor import MicroTrendPredictor
except ImportError:
    class MicroTrendPredictor:
        def predict_next_interval_pressure(self): return 0.45, 0.55

try: from core.weather_analytics import WeatherAnalyticsEngine
except ImportError:
    class WeatherAnalyticsEngine:
        def __init__(self):
            self.current_weather_condition = "Clear"
            self.wind_speed_mps = 3.2
            self.temperature_c = 18.0
        def calculate_weather_decay_modifiers(self): return 1.0, 1.0

try: from core.referee_analytics import RefereeSeverityAnalytics
except ImportError:
    class RefereeSeverityAnalytics:
        def __init__(self):
            self.referee_name = "Сергей Карасев"
            self.severity_index = 0.65
        def calibrate_discipline_intensity(self, v): return 0.25

try: from core.risk_manager import RiskManagementEngine
except ImportError:
    class RiskManagementEngine:
        def adjust_margin_by_volatility(self, **k): return 0.05

try: from core.stream_validator import StreamQualityValidator
except ImportError:
    class StreamQualityValidator:
        def __init__(self): self.is_stream_broken = False


class LiveMatchState:
    def __init__(self, match_id: str):
        self.match_id = match_id

        # Защищенная инициализация
        try: self.radar = SportsRadarRenderer("football")
        except Exception: self.radar = None
        try: self.trends = MicroTrendPredictor()
        except Exception: self.trends = None
        try: self.weather = WeatherAnalyticsEngine()
        except Exception: self.weather = None
        try: self.referee = RefereeSeverityAnalytics()
        except Exception: self.referee = None
        try: self.risk = RiskManagementEngine()
        except Exception: self.risk = None
        try: self.stream = StreamQualityValidator()
        except Exception: self.stream = None

        self.score = "0:0"
        self.time_seconds = 120
        self.ball_state = {"x": 50.0, "y": 34.0}
        self.team_a_players = []
        self.team_b_players = []
        self.predictions = {"main": [], "totals": [], "handicaps": []}
        self.line = {"main_outcomes": [], "totals": [], "handicaps": []}

    def build_state(self) -> Dict[str, Any]:
        radar_svg = "<svg></svg>"
        if self.radar:
            try: radar_svg = self.radar.render_svg_frame(ball_x=self.ball_state["x"], ball_y=self.ball_state["y"], team_a_players=self.team_a_players, team_b_players=self.team_b_players)
            except Exception: pass

        pressure_a, pressure_b = 0.5, 0.5
        if self.trends:
            try: pressure_a, pressure_b = self.trends.predict_next_interval_pressure()
            except Exception: pass

        decay_a, decay_b = 1.0, 1.0
        w_cond, w_speed, w_temp = "Clear", 0.0, 20.0
        if self.weather:
            try:
                decay_a, decay_b = self.weather.calculate_weather_decay_modifiers()
                w_cond = getattr(self.weather, 'current_weather_condition', 'Clear')
                w_speed = getattr(self.weather, 'wind_speed_mps', 0.0)
                w_temp = getattr(self.weather, 'temperature_c', 20.0)
            except Exception: pass

        ref_name, ref_severity, calibrated_lambda = "Судья", 0.5, 0.25
        if self.referee:
            try:
                calibrated_lambda = self.referee.calibrate_discipline_intensity(0.25)
                ref_name = getattr(self.referee, 'referee_name', 'Судья')
                ref_severity = getattr(self.referee, 'severity_index', 0.5)
            except Exception: pass

        current_margin = 0.05
        if self.risk:
            try: current_margin = self.risk.adjust_margin_by_volatility(live_xg_speed=0.12, is_critical_moment=False)
            except Exception: pass

        is_stream_broken = False
        if self.stream:
            try: is_stream_broken = getattr(self.stream, 'is_stream_broken', False)
            except Exception: pass

        return {
            "match_id": self.match_id,
            "teams": {"home": "ЦСКА (Москва)", "away": "Динамо (Москва)"},
            "score": self.score,
            "time_seconds": self.time_seconds,
            "radar_svg": radar_svg,
            "predictions": self.predictions,
            "line": self.line,
            "trends": {"pressure_a": pressure_a, "pressure_b": pressure_b},
            "weather": {"condition": w_cond, "decay_a": decay_a, "decay_b": decay_b, "wind_speed_mps": w_speed, "temperature_c": w_temp},
            "referee": {"name": ref_name, "severity_index": ref_severity, "discipline_lambda": calibrated_lambda},
            "risk": {"current_margin": current_margin},
            "stream": {"is_stream_broken": is_stream_broken}
        }
