# ============================================
# Prizolov Sports AI - Anti-Flicker Video Filter
# Version: 5.01 (Initial Architecture Release)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production CV Light Stabilization
# ============================================

import sys
import os
import cv2
import numpy as np
from typing import List, Optional

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import logging
logger = logging.getLogger("PrizolovSportsAI.FlickerFilter")

class AntiFlickerVideoFilter:
    """Аппаратный видеофильтр для динамического выравнивания яркости и гашения стробоскопического эффекта стадионных ламп"""

    def __init__(self, rolling_window_size: int = 15):
        self.window_size = rolling_window_size
        # Скользящий буфер средних значений яркости кадров
        self.brightness_history: List[float] = []
        self.target_brightness: Optional[float] = None

    def process_and_stabilize_light(self, frame: np.ndarray) -> np.ndarray:
        """
        Анализирует световую карту текущего кадра и выравнивает экспозицию под общий средний тренд матча.
        """
        if frame is None or frame.size == 0:
            return frame

        # Переводим кадр в пространство YCrCb, где канал Y отвечает за чистую яркость (Luminance)
        ycrcb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
        y_channel = ycrcb[:, :, 0]

        # Вычисляем среднюю глобальную яркость текущего кадра
        current_brightness = float(np.mean(y_channel))
        self.brightness_history.append(current_brightness)

        # Удерживаем размер скользящего окна памяти
        if len(self.brightness_history) > self.window_size:
            self.brightness_history.pop(0)

        # Вычисляем эталонную целевую яркость матча как скользящее среднее
        self.target_brightness = float(np.mean(self.brightness_history))

        # Расчет коэффициента отклонения яркости (мерцания)
        brightness_diff = self.target_brightness - current_brightness
        
        # Если мерцание незначительно (порог чувствительности детектора), возвращаем исходный кадр без затрат CPU
        if abs(brightness_diff) < 1.5:
            return frame

        # Рассчитываем множитель компенсации экспозиции
        gain = self.target_brightness / max(current_brightness, 0.1)
        # Ограничиваем рамки коррекции, чтобы не пережечь картинку при вспышках
        gain = max(min(gain, 1.3), 0.7)

        # Применяем векторизованное выравнивание экспозиции к каналу яркости Y
        adjusted_y = np.clip(y_channel * gain, 0, 255).astype(np.uint8)
        ycrcb[:, :, 0] = adjusted_y

        # Возвращаем стабилизированный кадр обратно в стандартный BGR формат для инференса YOLOv10
        stabilized_frame = cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)
        
        if abs(brightness_diff) > 8.0:
            logger.debug(f"[Anti-Flicker] Подавлено резкое мерцание света стадиона. Коррекция коэффициента: {gain:.2f}")

        return stabilized_frame
