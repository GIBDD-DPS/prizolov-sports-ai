# ============================================
# Prizolov Sports AI - Depth & Occlusion Filter
# Version: 5.02 (Minor Refactor & Cleanup)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: CV Tracking Occlusion Handling Core
#
# CHANGELOG (5.01 → 5.02):
# - Удалены неиспользуемые импорты (os, numpy, Tuple)
# - Убраны walrus-операторы для повышения совместимости и читаемости
# - Упрощена логика вычисления пересечения рамок
# - Добавлены точные типы и docstring-и
# - Оптимизирована структура кода без изменения логики
# ============================================

import sys
from pathlib import Path
from typing import List, Dict, Any

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class TrackingOcclusionFilter:
    """Модуль 3D-фильтрации взаимных перекрытий игроков на основе анализа масштаба рамок детекции."""

    def __init__(self, overlap_threshold: float = 0.55) -> None:
        """
        Args:
            overlap_threshold: Порог отношения площади пересечения к площади меньшей рамки,
                               выше которого считаем, что произошло значимое перекрытие.
        """
        self.overlap_thresh: float = overlap_threshold

    @staticmethod
    def _calculate_box_overlap_ratio(box_a: List[float], box_b: List[float]) -> float:
        """
        Рассчитывает отношение площади пересечения к площади меньшей из двух рамок.

        Args:
            box_a: [x1, y1, x2, y2] первой рамки.
            box_b: [x1, y1, x2, y2] второй рамки.

        Returns:
            Значение в диапазоне [0.0, 1.0], где 0.0 — нет пересечения,
            1.0 — меньшая рамка полностью перекрыта.
        """
        x1_a, y1_a, x2_a, y2_a = box_a
        x1_b, y1_b, x2_b, y2_b = box_b

        # Координаты пересечения
        xi1 = max(x1_a, x1_b)
        yi1 = max(y1_a, y1_b)
        xi2 = min(x2_a, x2_b)
        yi2 = min(y2_a, y2_b)

        inter_w = xi2 - xi1
        inter_h = yi2 - yi1

        if inter_w <= 0.0 or inter_h <= 0.0:
            return 0.0

        inter_area = inter_w * inter_h

        area_a = (x2_a - x1_a) * (y2_a - y1_a)
        area_b = (x2_b - x1_b) * (y2_b - y1_b)

        if area_a <= 0.0 or area_b <= 0.0:
            return 0.0

        min_area = min(area_a, area_b)
        return float(inter_area / min_area)

    def filter_occlusions(self, raw_detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Анализирует список детекций, выявляет перекрытия и маркирует игроков на переднем и заднем планах.

        Args:
            raw_detections:
                [{'track_id': 1, 'box': [x1, y1, x2, y2], 'meta': {...}}, ...]

        Returns:
            Тот же список детекций, дополненный полем:
                det["occlusion_status"] ∈ {"CLEAR", "FOREGROUND", "BACKGROUND_OCCLUDED"}.
        """
        num_det = len(raw_detections)
        if num_det < 2:
            return raw_detections

        # Статус по умолчанию
        for det in raw_detections:
            det["occlusion_status"] = "CLEAR"

        # Парные сравнения детекций
        for i in range(num_det):
            det_a = raw_detections[i]
            box_a = det_a["box"]

            for j in range(i + 1, num_det):
                det_b = raw_detections[j]
                box_b = det_b["box"]

                overlap = self._calculate_box_overlap_ratio(box_a, box_b)

                if overlap > self.overlap_thresh:
                    # Определяем, кто ближе к камере по нижней координате Y (y2)
                    y2_a = box_a[3]
                    y2_b = box_b[3]

                    if y2_a > y2_b:
                        det_a["occlusion_status"] = "FOREGROUND"
                        det_b["occlusion_status"] = "BACKGROUND_OCCLUDED"
                    else:
                        det_a["occlusion_status"] = "BACKGROUND_OCCLUDED"
                        det_b["occlusion_status"] = "FOREGROUND"

        return raw_detections
