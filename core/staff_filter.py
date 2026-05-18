# ============================================
# Prizolov Sports AI - Referee & Staff Filter Core
# Version: 5.01 (Initial Architecture Release)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: CV Player Detection Noise Reduction
# ============================================

import sys
import os
import cv2
import numpy as np
from typing import List, Dict, Any

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

class RefereeStaffFilter:
    """ИИ-процессор для детекции и исключения арбитров и стаффа из общего трекинга игроков"""

    def __init__(self):
        # Ограничения по HSV для классической яркой формы судей (например, неоновый желтый/салатовый)
        self.ref_hsv_low = np.array([25, 50, 70])
        self.ref_hsv_high = np.array([35, 255, 255])
        
        # Порог совпадения пикселей формы для признания силуэта судьей (30% площади джерси)
        self.color_match_threshold = 0.30

    def is_referee_by_color(self, player_crop: np.ndarray) -> bool:
        """Анализирует вырезанный силуэт игрока на наличие судейской расцветки формы"""
        if player_crop.size == 0:
            return False

        h, w, _ = player_crop.shape
        # Вырезаем верхнюю часть торса (зона рубашки/джерси)
        jersey_crop = player_crop[int(h*0.15):int(h*0.5), int(w*0.25):int(w*0.75)]
        if jersey_crop.size == 0:
            return False

        hsv = cv2.cvtColor(jersey_crop, cv2.COLOR_BGR2HSV)
        # Создаем бинарную маску по целевому судейскому цвету
        mask = cv2.inRange(hsv, self.ref_hsv_low, self.ref_hsv_high)
        
        match_ratio = np.count_nonzero(mask) / mask.size
        return match_ratio > self.color_match_threshold

    def filter_active_players(self, raw_detections: List[Dict[str, Any]], frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Проверяет все bounding box'ы кадра, вычищает из них судей и возвращает чистый список игроков.
        raw_detections: [{'track_id': 12, 'box': [x1, y1, x2, y2]}]
        """
        img_h, img_w, _ = frame.shape
        cleaned_detections = []

        for det in raw_detections:
            x1, y1, x2, y2 = det["box"]
            
            # Приведение к целочисленным координатам для безопасного вырезания из кадра
            ix1, iy1 = max(0, int(x1)), max(0, int(y1))
            ix2, iy2 = min(img_w, int(x2)), min(img_h, int(y2))
            
            player_crop = frame[iy1:iy2, ix1:ix2]
            
            # Проверяем ИИ-фильтром цвета. Если это судья — отбрасываем детекцию
            if self.is_referee_by_color(player_crop):
                continue
                
            cleaned_detections.append(det)

        return cleaned_detections
