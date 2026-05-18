# ============================================
# Prizolov Sports AI - Homography Calibrator
# Version: 5.10 (Full Headless Decoupling)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Video Pitch Perspective Transformation Matrix
# ============================================

import sys
import os
from pathlib import Path
from typing import List, Tuple, Optional, Any

class HomographyCalibrator:
    """Модуль вычисления матрицы гомографии для трансформации пикселей кадра в метры поля"""

    def __init__(self, sport: str):
        self.sport = sport.lower()
        self.h_matrix: Optional[Any] = None

    def get_static_football_pitch_anchors(self) -> List[Tuple[float, float]]:
        """Возвращает метрические координаты четырех угловых точек футбольного поля (105x68м)"""
        return [
            (0.0, 0.0),      # Левый верхний угол поля
            (105.0, 0.0),    # Правый верхний угол поля
            (105.0, 68.0),   # Правый нижний угол поля
            (0.0, 68.0)      # Левый нижний угол поля
        ]

    def compute_matrix(self, img_points: List[Tuple[float, float]], real_points: List[Tuple[float, float]]) -> Optional[Any]:
        """Безопасно вычисляет матрицу гомографии на основе C++ ядра OpenCV, если оно доступно"""
        if len(img_points) < 4 or len(real_points) < 4:
            return None
            
        try:
            # Локальный защищенный импорт для полного исключения падения libGL.so.1 при старте сервера
            import cv2
            import numpy as np
            
            pts_src = np.array(img_points, dtype=np.float32)
            pts_dst = np.array(real_points, dtype=np.float32)
            
            self.h_matrix, _ = cv2.findHomography(pts_src, pts_dst)
            return self.h_matrix
        except Exception:
            # Фолбэк-заглушка на случай отсутствия графических библиотек в Amvera Cloud
            self.h_matrix = None
            return None

    def transform_point(self, pixel_x: float, pixel_y: float) -> Tuple[float, float]:
        """Трансформирует экранные пиксели в реальные координаты (метры)"""
        if self.h_matrix is None:
            # Если OpenCV или калибровка недоступны, возвращаем координаты как есть (без проекции)
            return pixel_x, pixel_y
            
        try:
            import cv2
            import numpy as np
            
            px_vector = np.array([[[pixel_x, pixel_y]]], dtype=np.float32)
            transformed = cv2.perspectiveTransform(px_vector, self.h_matrix)
            return float(transformed[0][0][0]), float(transformed[0][0][1])
        except Exception:
            return pixel_x, pixel_y
