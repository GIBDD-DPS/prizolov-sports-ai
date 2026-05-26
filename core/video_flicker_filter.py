# ============================================
# Prizolov Sports AI - Anti-Flicker Video Filter
# Version: 5.02 (Minor Refactor & WP/Elementor Prep)
#
# CHANGELOG (5.01 → 5.02):
# - Добавлен отсутствующий импорт: from pathlib import Path
# - Уточнены типы и docstring-и
# - Упорядочены импорты
# - Лёгкая чистка структуры без изменения логики
# - Подготовка структуры под API-вывод статуса стабилизации для WordPress Elementor
#
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production CV Light Stabilization
# ============================================

import sys
import os
import cv2
import numpy as np
from pathlib import Path
from typing import List, Optional

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import logging
logger = logging.getLogger("PrizolovSportsAI.FlickerFilter")


class AntiFlickerVideoFilter:
    """
    Аппаратный видеофильтр для динамического выравнивания яркости
    и подавления стробоскопического эффекта стадионных ламп.
    Готов к сериализации в JSON для API-слоя WordPress Elementor.
    """

    def __init__(self, rolling_window_size: int = 15) -> None:
        """
        Args:
            rolling_window_size: размер скользящего окна усреднения яркости.
        """
        self.window_size = rolling_window_size
        self.brightness_history: List[float] = []
        self.target_brightness: Optional[float] = None

    def process_and_stabilize_light(self, frame: np.ndarray) -> np.ndarray:
        """
        Анализирует световую карту текущего кадра и выравнивает экспозицию
        под общий средний тренд матча.

        Returns:
            Стабилизированный кадр (np.ndarray).
        """
        if frame is None or frame.size == 0:
            return frame

        # Переводим кадр в YCrCb, где Y — яркость
        ycrcb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
        y_channel = ycrcb[:, :, 0]

        # Средняя яркость кадра
        current_brightness = float(np.mean(y_channel))
        self.brightness_history.append(current_brightness)

        # Удерживаем размер окна
        if len(self.brightness_history) > self.window_size:
            self.brightness_history.pop(0)

        # Целевая яркость — скользящее среднее
        self.target_brightness = float(np.mean(self.brightness_history))

        # Разница яркости
        brightness_diff = self.target_brightness - current_brightness

        # Если мерцание слабое — не тратим CPU
        if abs(brightness_diff) < 1.5:
            return frame

        # Коэффициент компенсации
        gain = self.target_brightness / max(current_brightness, 0.1)
        gain = max(min(gain, 1.3), 0.7)  # защита от пересвета

        # Выравнивание яркости
        adjusted_y = np.clip(y_channel * gain, 0, 255).astype(np.uint8)
        ycrcb[:, :, 0] = adjusted_y

        stabilized_frame = cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)

        if abs(brightness_diff) > 8.0:
            logger.debug(
                f"[Anti-Flicker] Подавлено резкое мерцание света. Коэффициент коррекции: {gain:.2f}"
            )

        return stabilized_frame
