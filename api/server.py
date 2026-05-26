# ============================================
# Prizolov Sports AI - Public API Gateway
# Version: 1.01 (Extended Live Match Endpoint)
#
# CHANGELOG:
# 1.01:
# - Создан единый расширенный endpoint /api/match/live/{match_id}
# - Интеграция с core-модулями: radar_renderer, trend_predictor,
#   weather_analytics, referee_analytics, risk_manager, stream_validator
# - Подготовка контракта под WordPress Elementor (расширенный JSON)
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
    version="1.01",
    description="Public JSON API for prizolov.ru sports widgets (WordPress / Elementor)."
)

# В проде сюда ставишь конкретный домен, сейчас — максимально открыто для интеграции
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _mock_live_state(match_id: str) -> Dict[str, Any]:
    """
    ВРЕМЕННЫЙ mock-орchestrator для архитектурного теста.
    Здесь в проде ты подключишь реальный live-буфер / брокер событий.
    """
    # 1. Радар (пока статический пример)
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
    # В реальности сюда перед каждым вызовом приходят update_metrics_history(...)
    pressure_a, pressure_b = trend.predict_next_interval_pressure()

    # 3. Погода
    weather = WeatherAnalyticsEngine()
    # В проде: weather.load_match_weather_report(...) из пре-матч фида
    decay_a, decay_b = weather.calculate_weather_decay_modifiers()

    # 4. Судья
    referee = RefereeSeverityAnalytics()
    # В проде: referee.load_referee_profile(...) из фида
    calibrated_lambda = referee.calibrate_discipline_intensity(0.25)

    # 5. Риск-менеджмент
    risk = RiskManagementEngine()
    current_margin = risk.adjust_margin_by_volatility(
        live_xg_speed=0.12,
        is_critical_moment=False
    )

    # 6. Стрим
    stream_validator = StreamQualityValidator()
    # В реальности статус берётся из live-лупа, здесь — просто флаг по умолчанию
    is_stream_broken = stream_validator.is_stream_broken

    # 7. Прогнозы и линия (пока заглушки под контракт)
    predictions = {
        "main": [
            # пример структуры:
            # {"market": "1X2", "outcome": "1", "prob": 0.52, "odds": 1.85}
        ],
        "totals": [],
        "handicaps": [],
    }

    line = {
        "main_outcomes": [],
        "totals": [],
        "handicaps": [],
    }

    return {
        "match_id": match_id,
        "teams": {
            "home": "ЦСКА (Москва)",
            "away": "Динамо (Москва)",
        },
        "score": "1:0",
        "time_seconds": 2610,
        "radar_svg": radar_svg,
        "predictions": predictions,
        "line": line,
        "trends": {
            "pressure_a": pressure_a,
            "pressure_b": pressure_b,
        },
        "weather": {
            "condition": weather.current_weather_condition,
            "decay_a": decay_a,
            "decay_b": decay_b,
            "wind_speed_mps": weather.wind_speed_mps,
            "temperature_c": weather.temperature_c,
        },
        "referee": {
            "name": referee.referee_name,
            "severity_index": referee.severity_index,
            "discipline_lambda": calibrated_lambda,
        },
        "risk": {
            "current_margin": current_margin,
        },
        "stream": {
            "is_stream_broken": is_stream_broken,
        },
    }


@app.get("/api/match/live/{match_id}")
def get_live_match_state(match_id: str) -> Dict[str, Any]:
    """
    Расширенный live-endpoint для интеграции с WordPress / Elementor.

    Возвращает:
    - команды, счёт, время
    - SVG-радар
    - прогнозы и линию
    - тренды давления
    - погодные модификаторы
    - профиль судьи
    - риск-менеджмент
    - статус стрима
    """
    # На первом этапе — mock-данные для матча ЦСКА–Динамо.
    # В проде здесь будет вызов реального orchestrator-а.
    return _mock_live_state(match_id)
