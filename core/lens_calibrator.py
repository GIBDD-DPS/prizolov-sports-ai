# ============================================
# Prizolov Sports AI - Lens Distortion Calibrator
# Version: 6.02 (+1.01: Safe OpenCV import, NaN protection, ROI guard,
#                 fallback mode, improved undistortPoints stability,
#                 unified style, WP-ready)
#
# CHANGELOG (что сделано):
# - Добавлен безопасный импорт OpenCV (fallback при отсутствии)
# - Добавлена защита от NaN/inf координат
# - Улучшена логика undistortPoints (проверка формы и NaN)
# - Улучшена обработка ROI (проверка границ)
# - Добавлен fallback-режим: если OpenCV недоступен → возвращаем исходный кадр
# - Улучшена структура кода и читаемость
# - Версия повышена на +1.01
#
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Optical Distortion Correction Core
# ============================================

import math
import numpy as np
from typing import Tuple, Optional


class LensDistortionCalibrator:
    """
    Модуль устранения радиальной и тангенциальной дисторсии вещательных камер.
    Используется перед гомографией для повышения точности координат.
    """

    def __init__(self, img_width: int = 1920, img_height: int = 1080):
        self.w = img_width
        self.h = img_height
        self.is_calibrated = False

        # Базовая матрица камеры (параметры усреднённого стадионного объектива)
        self.camera_matrix = np.array([
            [1500.0, 0.0, self.w / 2.0],
            [0.0, 1500.0, self.h / 2.0],
            [0.0, 0.0, 1.0]
        ], dtype=np.float32)

        # Радиальная и тангенциальная дисторсия
        self.dist_coeffs = np.array([-0.2, 0.1, 0.0, 0.0, 0.0], dtype=np.float32)

        self.new_camera_matrix = None
        self.roi = None

        self._optimize_matrix()

    # ============================================================
    # MATRIX OPTIMIZATION
    # ============================================================

    def _optimize_matrix(self) -> None:
        """Рассчитывает оптимальную новую матрицу камеры."""
        try:
            import cv2
            self.new_camera_matrix, self.roi = cv2.getOptimalNewCameraMatrix(
                self.camera_matrix,
                self.dist_coeffs,
                (self.w, self.h),
                0,
                (self.w, self.h)
            )
            self.is_calibrated = True
        except Exception:
            # OpenCV отсутствует → работаем в fallback-режиме
            self.new_camera_matrix = None
            self.roi = (0, 0, self.w, self.h)
            self.is_calibrated = False

    # ============================================================
    # CUSTOM CALIBRATION
    # ============================================================

    def set_custom_calibration(self, matrix: np.ndarray, coeffs: np.ndarray) -> None:
        """Загружает параметры камеры из JSON/YAML профиля."""
        self.camera_matrix = matrix.astype(np.float32)
        self.dist_coeffs = coeffs.astype(np.float32)
        self._optimize_matrix()

    # ============================================================
    # UNDISTORT FRAME
    # ============================================================

    def undistort_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Устраняет искажения линз на live‑кадре.
        """
        if not self.is_calibrated or self.new_camera_matrix is None:
            return frame

        try:
            import cv2

            undistorted = cv2.undistort(
                frame,
                self.camera_matrix,
                self.dist_coeffs,
                None,
                self.new_camera_matrix
            )

            x, y, w, h = self.roi

            # Проверка ROI
            if w > 0 and h > 0 and w <= undistorted.shape[1] and h <= undistorted.shape[0]:
                undistorted = undistorted[y:y + h, x:x + w]

            return undistorted

        except Exception:
            return frame

    # ============================================================
    # UNDISTORT POINTS
    # ============================================================

    def undistort_points(self, pixel_x: float, pixel_y: float) -> Tuple[float, float]:
        """
        Корректирует пиксельные координаты единичной детекции.
        Используется перед гомографией.
        """
        if not self.is_calibrated or self.new_camera_matrix is None:
            return pixel_x, pixel_y

        if not self._valid(pixel_x) or not self._valid(pixel_y):
            return pixel_x, pixel_y

        try:
            import cv2

            src_pt = np.array([[[pixel_x, pixel_y]]], dtype=np.float32)

            dst_pt = cv2.undistortPoints(
                src_pt,
                self.camera_matrix,
                self.dist_coeffs,
                None,
                self.new_camera_matrix
            )

            tx = float(dst_pt[0][0][0])
            ty = float(dst_pt[0][0][1])

            if not self._valid(tx) or not self._valid(ty):
                return pixel_x, pixel_y

            return tx, ty

        except Exception:
            return pixel_x, pixel_y

    # ============================================================
    # HELPERS
    # ============================================================

    @staticmethod
    def _valid(v: float) -> bool:
        return isinstance(v, (int, float)) and not math.isnan(v) and not math.isinf(v)
