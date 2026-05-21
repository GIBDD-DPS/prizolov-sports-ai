# ============================================
# Prizolov Sports AI - Depth & Occlusion Filter
# Version: 5.01 (Initial Architecture Release)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: CV Tracking Occlusion Handling Core
# ============================================

import sys
import os
from pathlib import Path

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import numpy as np
from typing import List, Dict, Any, Tuple

class TrackingOcclusionFilter:
    """Модуль 3D-фильтрации взаимных перекрытий игроков на основе анализа масштаба рамок детекции"""

    def __init__(self, overlap_threshold: float = 0.55):
        self.overlap_thresh = overlap_threshold

    def _calculate_box_overlap_ratio(self, box_a: List[float], box_b: List[float]) -> float:
        """Рассчитывает отношение площади пересечения к площади меньшей из двух рамок"""
        x1_a, y1_a, x2_a, y2_a = box_a
        x1_b, y1_b, x2_b, y2_b = box_b

        # Координаты пересечения
        xi1 = max(x1_a, xb1 := x1_b)
        yi1 = max(y1_a, yb1 := y1_b)
        xi2 = min(x2_a, xb2 := x2_b)
        yi2 = min(y2_a, yb2 := y2_b)

        inter_w = max(0.0, xi2 - xi1)
        inter_h = max(0.0, yi2 - yi1)
        inter_area = inter_w * inter_h

        if inter_area <= 0:
            return 0.0

        area_a = (x2_a - x1_a) * (y2_a - y1_a)
        area_b = (xb2 - xb1) * (yb2 - yb1)
        
        # Делим на площадь меньшего объекта (индикатор поглощения/перекрытия)
        min_area = min(area_a, area_b)
        return float(inter_area / min_area)

    def filter_occlusions(self, raw_detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Анализирует список детекций, выявляет перекрытия и маркирует игроков на переднем и заднем планах.
        raw_detections: [{'track_id': 1, 'box': [x1, y1, x2, y2], 'meta': {}}]
        """
        num_det = len(raw_detections)
        if num_det < 2:
            return raw_detections

        # Выставляем всем детекциям статус по умолчанию
        for det in raw_detections:
            det["occlusion_status"] = "CLEAR" # CLEAR, FOREGROUND, BACKGROUND_OCCLUDED

        for i in range(num_det):
            for j in range(i + 1, num_det):
                det_a = raw_detections[i]
                det_b = raw_detections[j]

                overlap = self._calculate_box_overlap_ratio(det_a["box"], det_b["box"])
                
                # Если зафиксировано критическое перекрытие силуэтов
                if overlap > self.overlap_thresh:
                    # Определяем, кто ближе к камере по нижней координате Y (Y2)
                    # В спортивной перспективе объект, чья нижняя граница на экране ниже, находится ближе к камере
                    y2_a = det_a["box"][3]
                    y2_b = det_b["box"][3]

                    if y2_a > y2_b:
                        det_a["occlusion_status"] = "FOREGROUND"
                        det_b["occlusion_status"] = "BACKGROUND_OCCLUDED"
                    else:
                        det_a["occlusion_status"] = "BACKGROUND_OCCLUDED"
                        det_b["occlusion_status"] = "FOREGROUND"

        return raw_detections
