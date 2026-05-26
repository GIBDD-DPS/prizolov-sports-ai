# ============================================
# Prizolov Sports AI - Micro-Trend Predictor
# Version: 4.02 (Minor Refactor & WP/Elementor Prep)
#
# CHANGELOG (4.01 → 4.02):
# - Уточнены типы и docstring-и
# - Упорядочено форматирование
# - Лёгкая чистка структуры без изменения логики
# - Подготовка структуры под API-вывод трендов для WordPress Elementor
#
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at prizolov.ru
# ============================================

import numpy as np
from typing import Dict, Any, List, Tuple


class MicroTrendPredictor:
    """
    Интеллектуальный блок прогнозирования краткосрочных live-трендов
    на базе скользящего временного окна.
    Готов к сериализации в JSON для API-слоя WordPress Elementor.
    """

    def __init__(self, window_size_frames: int = 1200) -> None:
        """
        Args:
            window_size_frames: размер окна анализа (1200 кадров при 20 FPS = 60 секунд игры).
        """
        self.window_size = window_size_frames

        # Буферы временных рядов для ключевых метрик
        self.history_possession_a: List[float] = []
        self.history_xg_a: List[float] = []
        self.history_xg_b: List[float] = []
        self.history_danger_attacks_a: List[int] = []
        self.history_danger_attacks_b: List[int] = []

    def _push_to_buffer(self, buffer: List[Any], value: Any) -> None:
        """
        Добавляет элемент в буфер и удерживает лимит скользящего окна.
        """
        buffer.append(value)
        if len(buffer) > self.window_size:
            buffer.pop(0)

    def update_metrics_history(self, current_metrics: Dict[str, Any]) -> None:
        """
        Помещает свежие метрики текущего кадра в буферы памяти.

        Args:
            current_metrics: словарь live-метрик текущего кадра.
        """
        self._push_to_buffer(self.history_possession_a, current_metrics.get("possession_a", 50.0))
        self._push_to_buffer(self.history_xg_a, current_metrics.get("xg_a", 0.0))
        self._push_to_buffer(self.history_xg_b, current_metrics.get("xg_b", 0.0))
        self._push_to_buffer(self.history_danger_attacks_a, current_metrics.get("dangerous_attacks_a", 0))
        self._push_to_buffer(self.history_danger_attacks_b, current_metrics.get("dangerous_attacks_b", 0))

    def _calculate_gradient(self, series: List[float]) -> float:
        """
        Вычисляет линейный тренд изменения метрики (производную) на отрезке времени.

        Returns:
            slope (float) — наклон линии тренда.
        """
        if len(series) < 10:
            return 0.0

        recent_data = np.array(series[-200:])
        if len(recent_data) < 2:
            return 0.0

        x = np.arange(len(recent_data))
        slope, _ = np.polyfit(x, recent_data, 1)
        return float(slope)

    def predict_next_interval_pressure(self) -> Tuple[float, float]:
        """
        Прогнозирует индекс атакующего давления на следующие 3–5 минут игры.

        Returns:
            (pressure_A, pressure_B) — множители интенсивности для команд.
        """
        if len(self.history_possession_a) < 100:
            return 1.0, 1.0

        # Тренды xG
        xg_slope_a = self._calculate_gradient(self.history_xg_a)
        xg_slope_b = self._calculate_gradient(self.history_xg_b)

        # Среднее владение за последнюю минуту
        recent_poss_a = np.mean(self.history_possession_a[-1200:])
        recent_poss_b = 100.0 - recent_poss_a

        # Алгоритм расчёта давления
        pressure_factor_a = (
            1.0
            + (max(xg_slope_a, 0.0) * 5.0)
            + (max(recent_poss_a - 60.0, 0.0) * 0.02)
        )

        pressure_factor_b = (
            1.0
            + (max(xg_slope_b, 0.0) * 5.0)
            + (max(recent_poss_b - 60.0, 0.0) * 0.02)
        )

        # Ограничение аномалий
        return min(pressure_factor_a, 2.0), min(pressure_factor_b, 2.0)
