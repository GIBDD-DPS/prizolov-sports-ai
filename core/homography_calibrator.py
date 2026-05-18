# ============================================
# Prizolov Sports AI - Homography Calibrator
# Version: 4.01 (Initial Architecture Release)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at prizolov.ru
# ============================================

import numpy as np
from typing import Tuple, List, Optional
import cv2

class HomographyCalibrator:
    """Модуль трансформации пиксельных координат видео в метрическую систему поля"""

    def __init__(self, sport: str):
        self.sport = sport.lower()
        self.h_matrix: Optional[np.ndarray] = None
        
        # Задаем эталонные размеры спортивных площадок по стандартам (в метрах)
        if self.sport == "football":
            self.real_width = 105.0
            self.real_height = 68.0
        elif self.sport == "hockey":
            self.real_width = 60.0
            self.real_height = 30.0
        elif self.sport == "basketball":
            self.real_width = 28.0
            self.real_height = 15.0
        else:
            self.real_width = 100.0
            self.real_height = 50.0

    def compute_matrix(self, image_points: List[Tuple[float, float]], real_points: List[Tuple[float, float]]) -> bool:
        """
        Вычисляет матрицу гомографии на основе минимум 4-х опорных точек.
        image_points: Координаты точек на видеокадре [(x1, y1), (x2, y2), ...]
        real_points: Координаты этих же точек на идеальной схеме поля в метрах [(x1, y1), ...]
        """
        if len(image_points) < 4 or len(real_points) < 4:
            return False
            
        pts_src = np.array(image_points, dtype=float)
        pts_dst = np.array(real_points, dtype=float)
        
        # Вычисление матрицы перспективного преобразования
        matrix, _ = cv2.findHomography(pts_src, pts_dst)
        
        if matrix is not None:
            self.h_matrix = matrix
            return True
        return False

    def transform_point(self, pixel_x: float, pixel_y: float) -> Tuple[float, float]:
        """Трансформирует пиксельную точку экрана в метры реального поля"""
        if self.h_matrix is None:
            # Если камера не откалибрована, возвращаем исходные пиксели как фолбэк
            return pixel_x, pixel_y
            
        point = np.array([[[pixel_x, pixel_y]]], dtype=float)
        # Применяем перспективное преобразование к точке
        transformed = cv2.perspectiveTransform(point, self.h_matrix)
        
        real_x = float(transformed[0][0][0])
        real_y = float(transformed[0][0][1])
        
        # Ограничиваем координаты физическими рамками поля (срезаем шумы)
        real_x = max(0.0, min(real_x, self.real_width))
        real_y = max(0.0, min(real_y, self.real_height))
        
        return real_x, real_y

    def get_static_football_pitch_anchors(self) -> List[Tuple[float, float]]:
        """Возвращает эталонные метрические координаты углов штрафной площади для футбола"""
        # Схема левой штрафной площади в метрах от левого верхнего угла поля (0,0)
        return [
            (0.0, 13.85),   # Верхний угол штрафной на лицевой линии
            (16.5, 13.85),  # Верхний внешний угол штрафной в поле
            (16.5, 54.15),  # Нижний внешний угол штрафной в поле
            (0.0, 54.15)    # Нижний угол штрафной на лицевой линии
        ]
