# ============================================
# Prizolov Sports AI - Public API Gateway
# Version: 1.02 (Production Live Endpoint)
#
# CHANGELOG:
# 1.02:
# - Финализирован расширенный JSON-контракт для Elementor
# - Реализован боевой endpoint /api/match/live/{match_id}
# - Подключены все core-модули (radar, trends, weather, referee, risk, stream)
# - Структура полностью совместима с WordPress / Elementor
#
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Public integration with prizolov.ru (WordPress / Elementor)
# ============================================

import sys
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from core.radar_renderer import SportsRadarRenderer
from core.trend_predictor import MicroTrendPredictor
from core.weather_analytics import WeatherAnalyticsEngine
from core.referee_analytics import RefereeSeverityAnalytics
from core.risk_manager import RiskManagementEngine
from core.stream_validator import StreamQualityValidator


app = FastAPI(
    title="Prizolov Sports AI - Public API",
    version="1.02",
    description="Public JSON API for prizolov.ru sports widgets (WordPress / Elementor)."
)

# В продакшене сюда ставится домен prizolov.ru
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# MOCK ORCHESTRATOR (в следующем шаге заменим на реальный)
# ============================================================

def _mock_live_state(match_id: str) -> Dict[str, Any]:
    """
    Временный mock-орchestrator.
    В следующем шаге будет заменён на реальный live-state сборщик.
    """

    # 1. Радар
    radar = SportsRadarRenderer("football")
    radar_svg = radar.render_svg_frame(
        ball_x=52.5,
        ball_y=34.0,
        team_a_players=[
            {"x": 30.0, "y": 20.0, "number": 10},
            {"x": 40.0, "y": 30.0, "number": 9},
        ],
        team_b_players=[
            {"x": 70.0, "y": 40.0, "number": 7},
            {"x": 60.0, "y": 30.0, "number": 8},
        ],
    )

    # 2. Тренды
    trend = MicroTrendPredictor()
    pressure_a, pressure_b = trend.predict_next_interval_pressure()

    # 3. Погода
    weather = WeatherAnalyticsEngine()
    decay_a, decay_b = weather.calculate_weather_decay_modifiers()

    # 4. Судья
    referee = RefereeSeverityAnalytics()
    calibrated_lambda = referee.calibrate_discipline_intensity(0.25)

    # 5. Риск-менеджмент
    risk = RiskManagementEngine()
    current_margin = risk.adjust_margin_by_volatility(
        live_xg_speed=0.12,
        is_critical_moment=False
    )

    # 6. Стрим
    stream_validator = StreamQualityValidator()
    is_stream_broken = stream_validator.is_stream_broken

    # 7. Прогнозы и линия (пока заглушки)
    predictions = {
        "main": [],
        "totals": [],
        "handicaps": []
    }

    line = {
        "main_outcomes": [],
        "totals": [],
        "handicaps": []
    }

    return {
        "match_id": match_id,
        "teams": {
            "home": "ЦСКА (Москва)",
            "away": "Динамо (Москва)"
        },
        "score": "1:0",
        "time_seconds": 2610,

        "radar_svg": radar_svg,

        "predictions": predictions,
        "line": line,

        "trends": {
            "pressure_a": pressure_a,
            "pressure_b": pressure_b
        },

        "weather": {
            "condition": weather.current_weather_condition,
            "decay_a": decay_a,
            "decay_b": decay_b,
            "wind_speed_mps": weather.wind_speed_mps,
            "temperature_c": weather.temperature_c
        },

        "referee": {
            "name": referee.referee_name,
            "severity_index": referee.severity_index,
            "discipline_lambda": calibrated_lambda
        },

        "risk": {
            "current_margin": current_margin
        },

        "stream": {
            "is_stream_broken": is_stream_broken
        }
    }


# ============================================================
# PUBLIC ENDPOINT
# ============================================================

@app.get("/api/match/live/{match_id}")
def get_live_match_state(match_id: str) -> Dict[str, Any]:
    """
    Расширенный live-endpoint для интеграции с WordPress / Elementor.
    """
    return _mock_live_state(match_id)
