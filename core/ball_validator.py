# ============================================
# Prizolov Sports AI - Ball/Puck Validation Core
# Version: 5.01 (Initial Architecture Release)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: CV Ball Tracking Noise Reduction
# ============================================

import sys
import os
import math
import logging
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

logger = logging.getLogger("PrizolovSportsAI.BallValidator")

class BallPuckValidator:
    """Интеллектуальный CV-модуль фильтрации аномалий и предиктивной валидации координат игрового снаряда"""

    def __init__(self, sport: str, fps: float = 25.0):
        self.sport = sport.lower()
        self.dt = 1.0 / fps
        
        # Задаем жесткие физические ограничения скоростей снарядов (в метрах в секунду)
        if self.sport == "football":
            self.max_physical_speed_mps = 45.0  # Максимальная скорость полета мяча после удара (~160 км/ч)
        elif self.sport == "hockey":
            self.max_physical_speed_mps = 55.0  # Скорость полета шайбы при щелчке щелчком (~200 км/ч)
        else:
            self.max_physical_speed_mps = 35.0

        # Память траектории движения в реальных метрах поля
        self.last_valid_x: Optional[float] = None
        self.last_valid_y: Optional[float] = None
        self.last_velocity_x = 0.0
        self.last_velocity_y = 0.0
        
        # Счетчик кадров непрерывной потери снаряда (для ограничения экстраполяции)
        self.lost_frames_counter = 0
        self.max_prediction_frames = 15 # Экстраполируем траекторию максимум 0.5 секунды

    def validate_and_smooth_trajectory(self, detected_x: float, detected_y: float, is_found_by_yolo: bool) -> Tuple[float, float, bool]:
        """
        Проверяет входящую детекцию на соответствие законам физики.
        Возвращает [valid_metric_x, valid_metric_y, is_ball_active].
        """
        # Сценарий 1: Нейросеть потеряла снаряд в текущем кадре (окклюзия)
        if not is_found_by_yolo or (detected_x == 0.0 and detected_y == 0.0):
            if self.last_valid_x is not None and self.lost_frames_counter < self.max_prediction_frames:
                self.lost_frames_counter += 1
                # Экстраполируем координаты по последнему вектору скорости (Траекторный Холдинг)
                pred_x = self.last_valid_x + (self.last_velocity_x * self.dt)
                pred_y = self.last_valid_y + (self.last_velocity_y * self.dt)
                
                self.last_valid_x = pred_x
                self.last_valid_y = pred_y
                return pred_x, pred_y, True
            return 0.0, 0.0, False

        # Если это самый первый кадр захвата снаряда
        if self.last_valid_x is None or self.last_valid_y is None:
            self.last_valid_x = detected_x
            self.last_valid_y = detected_y
            self.lost_frames_counter = 0
            return detected_x, detected_y, True

        # Сценарий 2: Снаряд обнаружен, проверяем мгновенный вектор скорости на законы физики
        distance_meters = math.sqrt((detected_x - self.last_valid_x) ** 2 + (detected_y - self.last_valid_y) ** 2)
        instant_speed_mps = distance_meters / self.dt

        if instant_speed_mps > self.max_physical_speed_mps:
            # Аномальный скачок координат! Признаем детекцию шумом и включаем предиктивный фолбэк
            logger.warning(
                f"[Trajectory Guard] Отброшена аномальная детекция снаряда! "
                f"Скорость: {instant_speed_mps:.1f} м/с превышает лимит {self.max_physical_speed_mps} м/с."
            )
            self.lost_frames_counter += 1
            if self.lost_frames_counter < self.max_prediction_frames:
                # Экстраполируем по затухающему вектору скорости (с учетом сопротивления воздуха/трения о лед)
                self.last_velocity_x *= 0.95
                self.last_velocity_y *= 0.95
                pred_x = self.last_valid_x + (self.last_velocity_x * self.dt)
                pred_y = self.last_valid_y + (self.last_velocity_y * self.dt)
                self.last_valid_x = pred_x
                self.last_valid_y = pred_y
                return pred_x, pred_y, True
            return 0.0, 0.0, False

        # Детекция успешна и физически валидна. Обновляем векторы скоростей для следующих итераций
        self.lost_frames_counter = 0
        self.last_velocity_x = (detected_x - self.last_valid_x) / self.dt
        self.last_velocity_y = (detected_y - self.last_valid_y) / self.dt
        
        self.last_valid_x = detected_x
        self.last_valid_y = detected_y
        
        return detected_x, detected_y, True
