# ============================================
# Prizolov Sports AI - Event Detection Core
# Version: 5.01 (Initial Architecture Release)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Real-time Match Event Extraction
# ============================================

import sys
import os
from pathlib import Path

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import logging
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger("PrizolovSportsAI.EventDetector")

class SportsEventDetector:
    """Интеллектуальный модуль детекции live-событий на основе пространственной геометрии снаряда"""

    def __init__(self, sport: str):
        self.sport = sport.lower()
        
        # Конфигурируем физические границы ворот по стандартам в метрах
        # Координаты X/Y относительно нулевой точки поля
        if self.sport == "football":
            self.goal_line_left = 0.0
            self.goal_line_right = 105.0
            # Створы ворот находятся по центру лицевой линии (ширина 7.32м)
            self.goal_y_top = 30.34
            self.goal_y_bottom = 37.66
        elif self.sport == "hockey":
            self.goal_line_left = 4.0 # За воротами в хоккее есть игровое пространство
            self.goal_line_right = 56.0
            self.goal_y_top = 14.0
            self.goal_y_bottom = 16.0
            
        # Память для расчета векторов ускорения и фиксации пересечений
        self.prev_ball_x: Optional[float] = None
        self.prev_ball_y: Optional[float] = None

    def analyze_ball_movement(self, ball_x: float, ball_y: float) -> Optional[Dict[str, Any]]:
        """
        Проверяет траекторию движения снаряда на пересечение ключевых линий разметки.
        Возвращает словарь события или None, если микро-событий не обнаружено.
        """
        if self.prev_ball_x is None or self.prev_ball_y is None:
            self.prev_ball_x = ball_x
            self.prev_ball_y = ball_y
            return None

        event_triggered = None

        if self.sport == "football":
            # Детекция гола в левые ворота (пересечение линии X=0 слева направо или наоборот в створе)
            if (self.prev_ball_x > 0.0 and ball_x <= 0.0) or (self.prev_ball_x <= 0.0 and ball_x > 0.0):
                if self.goal_y_top <= ball_y <= self.goal_y_bottom:
                    event_triggered = {"event_type": "GOAL_TEAM_B", "details": f"Зафиксирован гол в левые ворота на координате Y: {ball_y:.2f}м"}
            
            # Детекция гола в правые ворота (пересечение линии X=105)
            elif (self.prev_ball_x < 105.0 and ball_x >= 105.0) or (self.prev_ball_x >= 105.0 and ball_x < 105.0):
                if self.goal_y_top <= ball_y <= self.goal_y_bottom:
                    event_triggered = {"event_type": "GOAL_TEAM_A", "details": f"Зафиксирован гол в правые ворота на координате Y: {ball_y:.2f}м"}
                    
            # Детекция аута/вылета мяча за боковую линию (Y=0 или Y=68)
            elif (ball_y <= 0.0 or ball_y >= 68.0) and (0.0 < ball_x < 105.0):
                event_triggered = {"event_type": "OUT_OF_BOUNDS", "details": f"Мяч покинул боковую линию на отметке X: {ball_x:.2f}м"}

        elif self.sport == "basketball":
            # В баскетболе ball_y и ball_x проверяются на проход через кольцо, 
            # а также отслеживается заступ за трехочковую дугу. 
            # Для баскетбола вектор скорости VX используется как условная высота Z.
            pass

        # Сдвигаем память кадров
        self.prev_ball_x = ball_x
        self.prev_ball_y = ball_y

        if event_triggered:
            logger.info(f"[AI Event Extracted] Обнаружено событие: {event_triggered['event_type']} | {event_triggered['details']}")
            
        return event_triggered
