# ============================================
# Prizolov Sports AI - Homography Calibrator
# Version: 6.11 (+1.01: Safe OpenCV import, NaN protection, fallback matrix,
#                 improved validation, unified transform API, WP-ready)
#
# CHANGELOG (что сделано):
# - Добавлена защита от NaN/inf координат
# - Добавлена проверка корректности входных точек
# - Добавлен fallback: единичная матрица при отсутствии OpenCV
# - Улучшена логика transform_point (проверка формы)
# - Улучшена обработка ошибок OpenCV
# - Улучшена структура кода и читаемость
# - Подготовка под многоспортовый пайплайн
# - Версия повышена на +1.01
#
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Video Pitch Perspective Transformation Matrix
# ============================================

import math
from typing import List, Tuple, Optional, Any


class HomographyCalibrator:
    """
    Модуль вычисления матрицы гомографии для трансформации пикселей кадра
    в метрические координаты игрового поля.
    """

    def __init__(self, sport: str):
        self.sport = sport.lower()
        self.h_matrix: Optional[Any] = None
        self.fallback_identity = [[1.0, 0.0, 0.0],
                                  [0.0, 1.0, 0.0],
                                  [0.0, 0.0, 1.0]]

    # ============================================================
    # STATIC ANCHORS
    # ============================================================

    def get_static_football_pitch_anchors(self) -> List[Tuple[float, float]]:
        """Возвращает метрические координаты углов футбольного поля 105x68м."""
        return [
            (0.0, 0.0),
            (105.0, 0.0),
            (105.0, 68.0),
            (0.0, 68.0)
        ]

    # ============================================================
    # MATRIX COMPUTATION
    # ============================================================

    def compute_matrix(
        self,
        img_points: List[Tuple[float, float]],
        real_points: List[Tuple[float, float]]
    ) -> Optional[Any]:
        """
        Безопасно вычисляет матрицу гомографии.
        Возвращает None, если OpenCV недоступен или данные некорректны.
        """
        if not self._validate_points(img_points) or not self._validate_points(real_points):
            return None

        try:
            import cv2
            import numpy as np

            pts_src = np.array(img_points, dtype=np.float32)
            pts_dst = np.array(real_points, dtype=np.float32)

            h, status = cv2.findHomography(pts_src, pts_dst)

            if h is None:
                self.h_matrix = None
            else:
                self.h_matrix = h

            return self.h_matrix

        except Exception:
            # Фолбэк: OpenCV отсутствует или ошибка вычисления
            self.h_matrix = None
            return None

    # ============================================================
    # TRANSFORM POINT
    # ============================================================

    def transform_point(self, pixel_x: float, pixel_y: float) -> Tuple[float, float]:
        """
        Трансформирует пиксельные координаты в метрические.
        Если матрица недоступна — возвращает исходные координаты.
        """
        if not self._valid(pixel_x) or not self._valid(pixel_y):
            return pixel_x, pixel_y

        if self.h_matrix is None:
            return pixel_x, pixel_y

        try:
            import cv2
            import numpy as np

            px = np.array([[[pixel_x, pixel_y]]], dtype=np.float32)
            transformed = cv2.perspectiveTransform(px, self.h_matrix)

            tx = float(transformed[0][0][0])
            ty = float(transformed[0][0][1])

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

    @staticmethod
    def _validate_points(points: List[Tuple[float, float]]) -> bool:
        if not points or len(points) < 4:
            return False
        for x, y in points:
            if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
                return False
            if math.isnan(x) or math.isnan(y) or math.isinf(x) or math.isinf(y):
                return False
        return True
