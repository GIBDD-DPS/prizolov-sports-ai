# ============================================
# Prizolov Sports AI - Stream Quality Validator
# Version: 5.01 (Initial Architecture Release)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Video Stream Integrity & Anti-Fraud
# ============================================

import sys
import os
import cv2
import numpy as np
from typing import Dict, Any, Optional

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import logging
logger = logging.getLogger("PrizolovSportsAI.StreamValidator")

class StreamQualityValidator:
    """Модуль автоматического анализа качества видеосигнала и экстренной заморозки котировок при фризах трансляции"""

    def __init__(self, freeze_threshold_mse: float = 0.5, max_freeze_frames: int = 40):
        self.mse_threshold = freeze_threshold_mse
        self.max_freeze_frames = max_freeze_frames
        
        # Память для попиксельного сравнения
        self.prev_gray_frame: Optional[np.ndarray] = None
        self.freeze_counter = 0
        self.is_stream_broken = False

    def check_stream_integrity(self, current_frame: np.ndarray) -> bool:
        """
        Вычисляет отклонения матриц пикселей текущего и предыдущего фреймов вещания.
        Возвращает True, если поток стабилен, и False, если зафиксирована критическая аномалия (фриз).
        """
        if current_frame is None or current_frame.size == 0:
            logger.error("[Validator Alarm] Получен пустой или битый кадр из медиапотока!")
            self.is_stream_broken = True
            return False

        # Оптимизируем вычисления: переводим в градации серого и уменьшаем размер кадра для скоростного анализа
        gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
        small_gray = cv2.resize(gray, (160, 120))

        if self.prev_gray_frame is None:
            self.prev_gray_frame = small_gray
            return True

        # Расчет среднеквадратичной ошибки (MSE) между кадрами
        mse = np.mean((self.prev_gray_frame.astype(np.float32) - small_gray.astype(np.float32)) ** 2)
        self.prev_gray_frame = small_gray

        # Детекция черного экрана (если средняя яркость падает почти до нуля)
        avg_brightness = np.mean(small_gray)
        if avg_brightness < 2.0:
            logger.critical("[Validator Anti-Fraud] Обнаружен черный экран трансляции матча! Экстренная заморозка.")
            self.is_stream_broken = True
            return False

        # Проверка на полное отсутствие изменений (зависание / фриз картинки)
        if mse < self.mse_threshold:
            self.freeze_counter += 1
            if self.freeze_counter >= self.max_freeze_frames:
                if not self.is_stream_broken:
                    logger.critical(
                        f"[Validator Anti-Fraud] Зафиксировано глухое зависание трансляции "
                        f"на протяжении {self.freeze_counter} кадров! Блокировка букмекерской линии."
                    )
                self.is_stream_broken = True
                return False
        else:
            # Картинка живая, сбрасываем счетчик аномалий
            if self.is_stream_broken:
                logger.info("[Validator Recovery] Сигнал live-трансляции успешно восстановлен. Возобновление котировок.")
            self.freeze_counter = 0
            self.is_stream_broken = False

        return True
