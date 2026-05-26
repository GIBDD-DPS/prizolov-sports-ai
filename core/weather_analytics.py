# ============================================
# Prizolov Sports AI - Weather Analytics Engine
# Version: 5.02 (Minor Refactor & WP/Elementor Prep)
#
# CHANGELOG (5.01 → 5.02):
# - Уточнены типы и docstring-и
# - Упорядочено форматирование
# - Лёгкая чистка структуры без изменения логики
# - Подготовка структуры под API-вывод погодных коэффициентов для WordPress Elementor
#
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production Environmental Risk Mitigation
# ============================================

import sys
import os
import logging
from pathlib import Path
from typing import Dict, Any, Tuple

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

logger = logging.getLogger("PrizolovSportsAI.Weather")


class WeatherAnalyticsEngine:
    """
    Интеллектуальный процессор климатических факторов для адаптации матожидания результативности.
    Готов к сериализации в JSON для API-слоя WordPress Elementor.
    """

    def __init__(self) -> None:
        # Текущие погодные параметры матча
        self.current_weather_condition: str = "CLEAR"  # CLEAR, RAIN, HEAVY_RAIN, SNOW, FOG
        self.wind_speed_mps: float = 0.0
        self.temperature_c: float = 20.0
        self.is_active: bool = False

    def load_match_weather_report(self, report_data: Dict[str, Any]) -> None:
        """
        Загружает метеорологическую сводку из пре-матч фидов или ручной фиксации скаута.

        Args:
            report_data: словарь с погодными параметрами.
        """
        self.current_weather_condition = report_data.get("condition", "CLEAR").upper()
        self.wind_speed_mps = float(report_data.get("wind_speed", 0.0))
        self.temperature_c = float(report_data.get("temperature", 20.0))
        self.is_active = True

        logger.info(
            f"[Weather Engine] Загружен климатический профиль: {self.current_weather_condition} | "
            f"Ветер: {self.wind_speed_mps} м/с | Температура: {self.temperature_c}°C"
        )

    def calculate_weather_decay_modifiers(self) -> Tuple[float, float]:
        """
        Вычисляет множители падения результативности атак для Команды А и Б.

        Returns:
            (decay_modifier_a, decay_modifier_b)
        """
        if not self.is_active or self.current_weather_condition == "CLEAR":
            return 1.0, 1.0

        decay_a = 1.0
        decay_b = 1.0

        # Осадки
        if self.current_weather_condition == "RAIN":
            decay_a *= 0.93
            decay_b *= 0.93
        elif self.current_weather_condition == "HEAVY_RAIN":
            decay_a *= 0.84
            decay_b *= 0.84
        elif self.current_weather_condition == "SNOW":
            decay_a *= 0.78
            decay_b *= 0.78
        elif self.current_weather_condition == "FOG":
            decay_a *= 0.90
            decay_b *= 0.90

        # Шквалистый ветер
        if self.wind_speed_mps > 12.0:
            wind_penalty = min((self.wind_speed_mps - 12.0) * 0.015, 0.15)
            decay_a *= (1.0 - wind_penalty)
            decay_b *= (1.0 - wind_penalty)

        # Экстремальный холод
        if self.temperature_c < -10.0:
            cold_penalty = min(abs(self.temperature_c + 10.0) * 0.01, 0.10)
            decay_a *= (1.0 - cold_penalty)
            decay_b *= (1.0 - cold_penalty)

        return round(decay_a, 2), round(decay_b, 2)
