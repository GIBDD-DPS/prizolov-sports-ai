# ============================================
# Prizolov Sports AI - Raindrop & Lens Noise Filter
# Version: 6.02 (+1.01: stability improvements, NaN protection, 
#                 anti-drift mask, safe inpainting, CPU optimization,
#                 unified style, WP-ready)
#
# CHANGELOG (что сделано):
# - Добавлена защита от NaN/inf кадров
# - Улучшена логика накопления истории (анти-дрейф)
# - Добавлена проверка стабильности камеры (анти-ложные маски)
# - Улучшена фильтрация статических артефактов (капли, грязь)
# - Добавлена нормализация std-dev карты
# - Улучшена логика inpainting (ограничение площади + проверка маски)
# - Ускорена обработка (resize → 240p, float32 std)
# - Версия повышена на +1.01
#
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production CV Image Cleaning Core
# ============================================

import cv2
import numpy as np
import math
from typing import List, Optional
import logging

logger = logging.getLogger("PrizolovSportsAI.LensNoiseFilter")


class LensNoiseFilter:
    """
    Аппаратный CV‑процессор для обнаружения и нейтрализации капель воды,
    грязи и статических артефактов на защитном стекле камеры.
    """

    def __init__(self, history_size: int = 50, detection_threshold: int = 8):
        self.history_size = max(10, history_size)
        self.threshold = detection_threshold

        self.frame_buffer: List[np.ndarray] = []
        self.static_mask: Optional[np.ndarray] = None

        # Порог дрожания камеры (если камера двигается — маску не строим)
        self.camera_motion_threshold = 2.0

    # ============================================================
    # MAIN PROCESSOR
    # ============================================================

    def update_and_clean_lens_artifacts(self, frame: np.ndarray) -> np.ndarray:
        """
        Анализирует временную стабильность кадра, выжигает статический погодный шум
        и возвращает очищенное изображение для YOLOv10.
        """
        if frame is None or frame.size == 0:
            return frame

        # -----------------------------
        # Защита от NaN / inf
        # -----------------------------
        if not self._valid_frame(frame):
            return frame

        # -----------------------------
        # Преобразование в grayscale
        # -----------------------------
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Уменьшаем разрешение для ускорения
        small_gray = cv2.resize(gray, (320, 240), interpolation=cv2.INTER_AREA)

        # -----------------------------
        # Накопление истории
        # -----------------------------
        self.frame_buffer.append(small_gray.astype(np.float32))

        if len(self.frame_buffer) > self.history_size:
            self.frame_buffer.pop(0)

        # -----------------------------
        # Проверка дрожания камеры
        # -----------------------------
        if len(self.frame_buffer) >= 2:
            if self._camera_is_moving(self.frame_buffer[-2], self.frame_buffer[-1]):
                # Камера двигается → маску не обновляем
                return frame

        # -----------------------------
        # Построение маски статических артефактов
        # -----------------------------
        if len(self.frame_buffer) == self.history_size:
            std_dev = np.std(np.stack(self.frame_buffer, axis=0), axis=0)

            # Нормализация
            std_norm = cv2.normalize(std_dev, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

            # Инвертируем: низкое std → статический объект
            _, binary_mask = cv2.threshold(
                std_norm,
                self.threshold,
                255,
                cv2.THRESH_BINARY_INV
            )

            # Масштабируем под исходный кадр
            self.static_mask = cv2.resize(
                binary_mask,
                (frame.shape[1], frame.shape[0]),
                interpolation=cv2.INTER_NEAREST
            )

        # -----------------------------
        # Inpainting (восстановление)
        # -----------------------------
        if self.static_mask is not None:
            nonzero_ratio = np.count_nonzero(self.static_mask) / self.static_mask.size

            # Ограничение: не более 15% кадра
            if 0 < nonzero_ratio < 0.15:
                try:
                    cleaned = cv2.inpaint(
                        frame,
                        self.static_mask,
                        inpaintRadius=5,
                        flags=cv2.INPAINT_NS
                    )
                    return cleaned
                except Exception:
                    return frame

        return frame

    # ============================================================
    # HELPERS
    # ============================================================

    @staticmethod
    def _valid_frame(frame: np.ndarray) -> bool:
        """Проверка на NaN/inf."""
        return not (np.isnan(frame).any() or np.isinf(frame).any())

    def _camera_is_moving(self, prev: np.ndarray, curr: np.ndarray) -> bool:
        """
        Проверяет дрожание камеры по среднему абсолютному отклонению.
        Если камера двигается — маску не строим.
        """
        diff = np.mean(np.abs(curr - prev))
        return diff > self.camera_motion_threshold
