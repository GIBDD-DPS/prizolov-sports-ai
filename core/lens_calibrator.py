# ============================================
# Prizolov Sports AI - Lens Distortion Calibrator
# Version: 5.01 (Initial Architecture Release)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Optical Distortion Correction Core
# ============================================

import sys
import os
from pathlib import Path

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import cv2
import numpy as np
from typing import Tuple, Optional

class LensDistortionCalibrator:
    """Модуль устранения радиальной и тангенциальной дисторсии вещательных камер (Анти-Рыбий Глаз)"""

    def __init__(self, img_width: int = 1920, img_height: int = 1080):
        self.w = img_width
        self.h = img_height
        self.is_calibrated = False

        # Внутренние параметры камеры (Camera Matrix и Distortion Coefficients)
        # Инициализируются дефолтными значениями под среднефокусные стадионные объективы
        self.camera_matrix = np.array([
            [1500.0, 0.0, self.w / 2.0],
            [0.0, 1500.0, self.h / 2.0],
            [0.0, 0.0, 1.0]
        ], dtype=np.float32)
        
        # Коэффициенты радиальной (k1, k2, k3) и тангенциальной (p1, p2) дисторсии
        self.dist_coeffs = np.array([-0.2, 0.1, 0.0, 0.0, 0.0], dtype=np.float32)
        
        self.new_camera_matrix = None
        self.roi = None
        self._optimize_matrix()

    def _optimize_matrix(self) -> None:
        """Рассчитывает оптимальную новую матрицу камеры на основе баланса сохранения пикселей (Alpha=0)"""
        self.new_camera_matrix, self.roi = cv2.getOptimalNewCameraMatrix(
            self.camera_matrix, self.dist_coeffs, (self.w, self.h), 0, (self.w, self.h)
        )
        self.is_calibrated = True

    def set_custom_calibration(self, matrix: np.ndarray, coeffs: np.ndarray) -> None:
        """Позволяет загрузить точные параметры профиля камеры из JSON/YAML конфигурации матча"""
        self.camera_matrix = matrix.astype(np.float32)
        self.dist_coeffs = coeffs.astype(np.float32)
        self._optimize_matrix()

    def undistort_frame(self, frame: np.ndarray) -> np.ndarray:
        """Выпрямляет live-кадр трансляции, устраняя искажения линз и бочкообразность контуров"""
        if not self.is_calibrated or self.new_camera_matrix is None:
            return frame

        # Выпрямление кадра на C++ ядре OpenCV
        undistorted = cv2.undistort(frame, self.camera_matrix, self.dist_coeffs, None, self.new_camera_matrix)
        
        # Обрезаем черные края, если это необходимо по результатам ROI
        x, y, w, h = self.roi
        if w > 0 and h > 0:
            undistorted = undistorted[y:y+h, x:x+w]
            
        return undistorted

    def undistort_points(self, pixel_x: float, pixel_y: float) -> Tuple[float, float]:
        """Корректирует пиксельные координаты единичной детекции перед передачей в модуль гомографии"""
        if not self.is_calibrated or self.new_camera_matrix is None:
            return pixel_x, pixel_y

        src_pt = np.array([[[pixel_x, pixel_y]]], dtype=np.float32)
        # Вычисление идеальной недеформированной пиксельной позиции объекта
        dst_pt = cv2.undistortPoints(src_pt, self.camera_matrix, self.dist_coeffs, None, self.new_camera_matrix)
        
        return float(dst_pt[0][0][0]), float(dst_pt[0][0][1])
