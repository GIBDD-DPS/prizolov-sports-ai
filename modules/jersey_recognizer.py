# ============================================
# Prizolov Sports AI - Jersey & Team Recognizer
# Version: 5.01 (Initial Architecture Release)
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

import cv2
import numpy as np
from typing import Tuple, Optional, List

class JerseyTeamRecognizer:
    """ИИ-модуль распознавания принадлежности к команде по цвету формы (HSV + K-Means)"""

    def __init__(self):
        # Эталонные цветовые центры для Команды А и Команды Б в пространстве HSV
        # Будут динамически калиброваться в первые 30 секунд матча
        self.team_a_hsv_center: Optional[np.ndarray] = None
        self.team_b_hsv_center: Optional[np.ndarray] = None
        self.is_calibrated: bool = False

    def calibrate_teams(self, sample_jerseys_a: List[np.ndarray], sample_jerseys_b: List[np.ndarray]) -> None:
        """Калибрует базовые цвета команд на основе ручных пресетов или стартовых кадров"""
        def _get_average_hsv(samples: List[np.ndarray]) -> np.ndarray:
            h_list, s_list, v_list = [], [], []
            for img in samples:
                if img.size == 0:
                    continue
                hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
                h_list.append(np.mean(hsv[:, :, 0]))
                s_list.append(np.mean(hsv[:, :, 1]))
                v_list.append(np.mean(hsv[:, :, 2]))
            return np.array([np.mean(h_list), np.mean(s_list), np.mean(v_list)])

        if sample_jerseys_a and sample_jerseys_b:
            self.team_a_hsv_center = _get_average_hsv(sample_jerseys_a)
            self.team_b_hsv_center = _get_average_hsv(sample_jerseys_b)
            self.is_calibrated = True

    def segment_jersey_color(self, player_crop: np.ndarray) -> Tuple[float, float, float]:
        """
        Вырезает фон, берет только центральную часть торса игрока 
        и возвращает доминирующий HSV цвет с помощью K-Means.
        """
        if player_crop.size == 0:
            return 0.0, 0.0, 0.0

        h, w, _ = player_crop.shape
        # Берем только центральные 40% по горизонтали и вертикали (зона джерси без рук и ног)
        torso_crop = player_crop[int(h*0.2):int(h*0.6), int(w*0.3):int(w*0.7)]
        
        if torso_crop.size == 0:
            return 0.0, 0.0, 0.0

        # Переводим в HSV
        hsv_torso = cv2.cvtColor(torso_crop, cv2.COLOR_BGR2HSV)
        
        # Решейпим массив пикселей для K-Means кластеризации
        pixels = hsv_torso.reshape((-1, 3)).astype(np.float32)
        
        # Настройки K-Means (ищем 2 главных цвета: цвет формы и цвет деталей/номера)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        flags = cv2.KMEANS_RANDOM_CENTERS
        _, labels, centers = cv2.kmeans(pixels, 2, None, criteria, 10, flags)
        
        # Находим самый часто встречающийся кластер
        counts = np.bincount(labels.flatten())
        dominant_center = centers[np.argmax(counts)]
        
        return float(dominant_center[0]), float(dominant_center[1]), float(dominant_center[2])

    def predict_team(self, player_crop: np.ndarray) -> Optional[str]:
        """Определяет команду игрока ("A" или "B") на основе евклидова расстояния в HSV"""
        if not self.is_calibrated or self.team_a_hsv_center is None or self.team_b_hsv_center is None:
            return None

        dom_h, dom_s, dom_v = self.segment_jersey_color(player_crop)
        if dom_h == 0.0 and dom_s == 0.0:
            return None

        current_hsv = np.array([dom_h, dom_s, dom_v])
        
        # Весовые коэффициенты для HSV расстояния (тон H важнее, чем яркость V)
        weights = np.array([1.0, 0.5, 0.3])
        
        dist_a = np.sqrt(np.sum(((current_hsv - self.team_a_hsv_center) * weights) ** 2))
        dist_b = np.sqrt(np.sum(((current_hsv - self.team_b_hsv_center) * weights) ** 2))
        
        return "A" if dist_a < dist_b else "B"

    def preprocess_number_ocr(self, player_crop: np.ndarray) -> Optional[np.ndarray]:
        """Подготавливает изображение спины/груди игрока для OCR-модулей распознавания номеров"""
        if player_crop.size == 0:
            return None
            
        # Переводим в градации серого
        gray = cv2.cvtColor(player_crop, cv2.COLOR_BGR2GRAY)
        
        # Увеличиваем контрастность адаптивным выравниванием гистограммы (CLAHE)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        contrast = clahe.apply(gray)
        
        # Бинаризация Оцу для выделения четких контуров цифр номера
        _, thresh = cv2.threshold(contrast, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return thresh
