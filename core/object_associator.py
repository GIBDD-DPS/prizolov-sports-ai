# ============================================
# Prizolov Sports AI - Object Association Core
# Version: 5.01 (Initial Architecture Release)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: High-Accuracy Multi-Object Tracking
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
from scipy.optimize import linear_sum_assignment

class SportsObjectAssociator:
    """Математическое ядро ассоциации объектов для минимизации потерь ID трекинга при пересечениях"""

    def __init__(self, max_lost_frames: int = 30):
        self.max_lost_frames = max_lost_frames
        # Хранилище активных треков: {track_id: {"box": [x1,y1,x2,y2], "lost_counter": 0, "meta": {}}}
        self.active_tracks: Dict[int, Dict[str, Any]] = {}
        self.next_track_id = 0

    def _calculate_iou(self, box_a: List[float], box_b: List[float]) -> float:
        """Вычисляет метрику IoU (Intersection over Union) для двух прямоугольных рамок детекции"""
        xa1, ya1, xa2, ya2 = box_a
        xb1, yb1, xb2, yb2 = box_b

        # Определение координат пересечения
        xi1 = max(xa1, xb1)
        yi1 = max(ya1, yb1)
        xi2 = min(xa2, xb2)
        yi2 = min(ya2, yb2)

        inter_width = max(0.0, xi2 - xi1)
        inter_height = max(0.0, yi2 - yi1)
        inter_area = inter_width * inter_height

        # Расчет площадей исходных рамок
        area_a = (xa2 - xa1) * (ya2 - ya1)
        area_b = (xb2 - xb1) * (yb2 - yb1)
        union_area = area_a + area_b - inter_area

        if union_area <= 0:
            return 0.0
        return float(inter_area / union_area)

    def associate_detections(self, new_detections: List[Dict[str, Any]], iou_threshold: float = 0.3) -> List[Dict[str, Any]]:
        """
        Сопоставляет новые детекции с текущими треками с помощью Венгерского алгоритма.
        new_detections: [{'box': [x1, y1, x2, y2], 'meta': {}}]
        """
        track_ids = list(self.active_tracks.keys())
        
        # Если активных треков или новых детекций нет, инициализируем базу заново
        if not track_ids or not new_detections:
            updated_detections = []
            for det in new_detections:
                self.next_track_id += 1
                self.active_tracks[self.next_track_id] = {"box": det["box"], "lost_counter": 0, "meta": det.get("meta", {})}
                det["track_id"] = self.next_track_id
                updated_detections.append(det)
            return updated_detections

        # Построение матрицы стоимости (Cost Matrix) на основе инвертированного IoU
        cost_matrix = np.zeros((len(track_ids), len(new_detections)), dtype=np.float32)
        for t_idx, t_id in enumerate(track_ids):
            for d_idx, det in enumerate(new_detections):
                iou = self._calculate_iou(self.active_tracks[t_id]["box"], det["box"])
                cost_matrix[t_idx, d_idx] = 1.0 - iou

        # Применение Венгерского алгоритма для минимизации суммарной стоимости ошибок сопоставления
        track_ind, det_ind = linear_sum_assignment(cost_matrix)

        matched_tracks = set()
        matched_detections = set()

        # Обработка успешных сопоставлений
        for t_idx, d_idx in zip(track_ind, det_ind):
            t_id = track_ids[t_idx]
            det = new_detections[d_idx]
            iou = 1.0 - cost_matrix[t_idx, d_idx]

            # Если пересечение выше порога, обновляем трек
            if iou >= iou_threshold:
                self.active_tracks[t_id]["box"] = det["box"]
                self.active_tracks[t_id]["lost_counter"] = 0
                det["track_id"] = t_id
                matched_tracks.add(t_id)
                matched_detections.add(d_idx)

        # Обработка несовпавших треков (игрок временно скрылся из кадра)
        for t_id in track_ids:
            if t_id not in matched_tracks:
                self.active_tracks[t_id]["lost_counter"] += 1
                # Если цель потеряна слишком долго, удаляем её из оперативной памяти
                if self.active_tracks[t_id]["lost_counter"] > self.max_lost_frames:
                    del self.active_tracks[t_id]

        # Обработка новых детекций (появился новый игрок на поле/лед вошел в кадр)
        for d_idx, det in enumerate(new_detections):
            if d_idx not in matched_detections:
                self.next_track_id += 1
                self.active_tracks[self.next_track_id] = {"box": det["box"], "lost_counter": 0, "meta": det.get("meta", {})}
                det["track_id"] = self.next_track_id

        return new_detections
