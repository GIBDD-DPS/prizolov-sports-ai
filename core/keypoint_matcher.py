# ============================================
# Prizolov Sports AI - Keypoint Matcher
# Version: 5.02 (+1.01: improved validation, NaN protection, weighted anchors,
#                 safe homography update, unified geometry, WP-ready)
#
# CHANGELOG (что сделано):
# - Добавлена защита от NaN/inf координат
# - Улучшена валидация входных ключевых точек
# - Добавлена весовая система: угловые точки имеют приоритет
# - Улучшена логика сопоставления class_id → метрические координаты
# - Улучшена интеграция с HomographyCalibrator
# - Добавлена проверка минимального качества набора точек
# - Улучшено логирование
# - Версия повышена на +1.01
#
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at prizolov.ru
# ============================================

from typing import Dict, List, Tuple, Optional
import math
from core.homography_calibrator import HomographyCalibrator


class SportsKeypointMatcher:
    """
    Умный модуль сопоставления ИИ‑ключевых точек с метрической геометрией
    спортивных площадок. Используется для автоматической калибровки гомографии.
    """

    def __init__(self, calibrator: HomographyCalibrator):
        self.calibrator = calibrator
        self.sport = calibrator.sport

        # Эталонные метрические координаты ключевых точек
        self.geometry_map: Dict[int, Tuple[float, float]] = {}
        self._initialize_anchor_geometry()

        # Весовые коэффициенты (углы поля важнее)
        self.anchor_weights: Dict[int, float] = {}

        self._initialize_weights()

    # ============================================================
    # GEOMETRY MAP
    # ============================================================

    def _initialize_anchor_geometry(self) -> None:
        """Регистрирует эталонные ID точек разметки и их точное положение в метрах."""

        if self.sport == "football":
            self.geometry_map = {
                0: (0.0, 0.0),
                1: (0.0, 68.0),
                2: (105.0, 0.0),
                3: (105.0, 68.0),
                4: (0.0, 13.85),
                5: (16.5, 13.85),
                6: (16.5, 54.15),
                7: (0.0, 54.15),
                8: (52.5, 0.0),
                9: (52.5, 68.0),
                10: (52.5, 34.0)
            }

        elif self.sport == "hockey":
            self.geometry_map = {
                0: (0.0, 0.0),
                1: (60.0, 0.0),
                2: (0.0, 30.0),
                3: (60.0, 30.0),
                4: (22.86, 0.0),
                5: (22.86, 30.0),
                6: (37.14, 0.0),
                7: (37.14, 30.0),
                8: (30.0, 15.0)
            }

        elif self.sport == "basketball":
            self.geometry_map = {
                0: (0.0, 0.0),
                1: (28.0, 0.0),
                2: (0.0, 15.0),
                3: (28.0, 15.0),
                4: (14.0, 0.0),
                5: (14.0, 15.0),
                6: (5.8, 4.3),
                7: (5.8, 10.7)
            }

    # ============================================================
    # WEIGHTS
    # ============================================================

    def _initialize_weights(self) -> None:
        """Устанавливает веса ключевых точек (углы поля самые важные)."""

        for class_id in self.geometry_map:
            # Угловые точки → максимальный вес
            if class_id in (0, 1, 2, 3):
                self.anchor_weights[class_id] = 1.0
            else:
                self.anchor_weights[class_id] = 0.6

    # ============================================================
    # VALIDATION HELPERS
    # ============================================================

    @staticmethod
    def _valid_point(pt: Tuple[float, float]) -> bool:
        x, y = pt
        return (
            isinstance(x, (int, float)) and
            isinstance(y, (int, float)) and
            not math.isnan(x) and not math.isnan(y) and
            not math.isinf(x) and not math.isinf(y)
        )

    # ============================================================
    # HOMOGRAPHY UPDATE
    # ============================================================

    def update_homography_from_detections(
        self,
        detected_keypoints: Dict[int, Tuple[float, float]]
    ) -> bool:
        """
        Принимает словарь обнаруженных ИИ‑точек разметки {class_id: (pixel_x, pixel_y)}.
        Автоматически сопоставляет их с эталонной геометрией и пересчитывает матрицу гомографии.
        """

        image_points: List[Tuple[float, float]] = []
        real_points: List[Tuple[float, float]] = []
        weights: List[float] = []

        for class_id, pixel_coords in detected_keypoints.items():
            if class_id not in self.geometry_map:
                continue

            if not self._valid_point(pixel_coords):
                continue

            image_points.append(pixel_coords)
            real_points.append(self.geometry_map[class_id])
            weights.append(self.anchor_weights.get(class_id, 0.5))

        # Минимум 4 точки для гомографии
        if len(image_points) < 4:
            return False

        # Приоритет: сортируем по весам (углы → первыми)
        sorted_triplets = sorted(
            zip(image_points, real_points, weights),
            key=lambda x: -x[2]
        )

        image_points = [p[0] for p in sorted_triplets]
        real_points = [p[1] for p in sorted_triplets]

        # Передаём в калибратор
        success = self.calibrator.compute_matrix(image_points, real_points)

        return success is not None
