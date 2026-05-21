# ============================================
# Prizolov Sports AI - Keypoint Matcher
# Version: 4.01 (Initial Architecture Release)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at prizolov.ru
# ============================================

import sys
import os
from pathlib import Path

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from typing import Dict, List, Tuple, Optional
from core.homography_calibrator import HomographyCalibrator

class SportsKeypointMatcher:
    """Умный модуль сопоставления ИИ-ключевых точек с метрической геометрией спортивных площадок"""

    def __init__(self, calibrator: HomographyCalibrator):
        self.calibrator = calibrator
        self.sport = calibrator.sport
        
        # Словарь эталонных метрических координат (X, Y) ключевых точек по стандартам видов спорта
        self.geometry_map: Dict[int, Tuple[float, float]] = {}
        self._initialize_anchor_geometry()

    def _initialize_anchor_geometry(self) -> None:
        """Регистрирует эталонные ID точек разметки и их точное положение на поле в метрах (0,0 - левый верхний угол)"""
        if self.sport == "football":
            self.geometry_map = {
                0: (0.0, 0.0),       # Левый верхний угловой флаг
                1: (0.0, 68.0),      # Левый нижний угловой флаг
                2: (105.0, 0.0),     # Правый верхний угловой флаг
                3: (105.0, 68.0),    # Правый нижний угловой флаг
                4: (0.0, 13.85),     # Левая штрафная: верхнее пересечение с лицевой
                5: (16.5, 13.85),    # Левая штрафная: верхний внешний угол
                6: (16.5, 54.15),    # Левая штрафная: нижний внешний угол
                7: (0.0, 54.15),     # Левая штрафная: нижнее пересечение с лицевой
                8: (52.5, 0.0),      # Центральная линия: верхнее пересечение с боковой
                9: (52.5, 68.0),     # Центральная линия: нижнее пересечение с боковой
                10: (52.5, 34.0)     # Точка в центре поля
            }
        elif self.sport == "hockey":
            self.geometry_map = {
                0: (0.0, 0.0),       # Левый верхний угол (аппроксимация борта)
                1: (60.0, 0.0),      # Правый верхний угол
                2: (0.0, 30.0),      # Левый нижний угол
                3: (60.0, 30.0),     # Правый нижний угол
                4: (22.86, 0.0),     # Левая синяя линия: верхний борт
                5: (22.86, 30.0),    # Левая синяя линия: нижний борт
                6: (37.14, 0.0),     # Правая синяя линия: верхний борт
                7: (37.14, 30.0),    # Правая синяя линия: нижний борт
                8: (30.0, 15.0)      # Центральная точка вбрасывания
            }
        elif self.sport == "basketball":
            self.geometry_map = {
                0: (0.0, 0.0),       # Левый верхний угол площадки
                1: (28.0, 0.0),      # Правый верхний угол
                2: (0.0, 15.0),      # Левый нижний угол
                3: (28.0, 15.0),     # Правый нижний угол
                4: (14.0, 0.0),      # Центральная линия: верх
                5: (14.0, 15.0),     # Центральная линия: низ
                6: (5.8, 4.3),       # Левая штрафная линия: верхний угол
                7: (5.8, 10.7)       # Левая штрафная линия: нижний угол
            }

    def update_homography_from_detections(self, detected_keypoints: Dict[int, Tuple[float, float]]) -> bool:
        """
        Принимает словарь обнаруженных ИИ-точек разметки {class_id: (pixel_x, pixel_y)}.
        Автоматически находит соответствия, фильтрует и пересчитывает матрицу калибратора.
        """
        image_points: List[Tuple[float, float]] = []
        real_points: List[Tuple[float, float]] = []

        for class_id, pixel_coords in detected_keypoints.items():
            if class_id in self.geometry_map:
                image_points.append(pixel_coords)
                real_points.append(self.geometry_map[class_id])

        # Для вычисления гомографии строго необходимо минимум 4 точки разметки в кадре
        if len(image_points) < 4:
            return False

        # Передаем отфильтрованные массивы точек в калибратор для расчета матрицы преобразования
        success = self.calibrator.compute_matrix(image_points, real_points)
        return success
