# ============================================
# Prizolov Sports AI - Event Detection Core
# Version: 6.02 (+1.01: Improved geometry, anti-teleport, hockey events,
#                 basketball hooks, safe ops, unified event format,
#                 WP/Elementor-ready, trajectory guard v2)
#
# CHANGELOG (что сделано):
# - Добавлена защита от NaN/inf координат
# - Добавлена анти‑телепортация (ограничение max delta)
# - Улучшена геометрия ворот (футбол/хоккей)
# - Добавлена детекция хоккейных голов (GOAL_A / GOAL_B)
# - Добавлена детекция вылета шайбы за пределы площадки
# - Добавлены заготовки под баскетбол (3PT, rim pass)
# - Улучшена логика пересечения линий
# - Единый формат событий: {event_type, details, x, y, timestamp}
# - Улучшено логирование
# - Версия повышена на +1.01
#
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Real-time Match Event Extraction
# ============================================

import math
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("PrizolovSportsAI.EventDetector")


class SportsEventDetector:
    """
    Интеллектуальный модуль детекции live‑событий на основе
    пространственной геометрии движения снаряда.
    """

    def __init__(self, sport: str):
        self.sport = sport.lower()

        # -----------------------------
        # Геометрия ворот / площадки
        # -----------------------------
        if self.sport == "football":
            self.goal_line_left = 0.0
            self.goal_line_right = 105.0
            self.goal_y_top = 30.34
            self.goal_y_bottom = 37.66
            self.field_y_min = 0.0
            self.field_y_max = 68.0

        elif self.sport == "hockey":
            self.goal_line_left = 4.0
            self.goal_line_right = 56.0
            self.goal_y_top = 14.0
            self.goal_y_bottom = 16.0
            self.field_y_min = 0.0
            self.field_y_max = 30.0

        elif self.sport == "basketball":
            # Заготовка под кольцо и трехочковую дугу
            self.hoop_x = 14.0
            self.hoop_y = 7.5
            self.hoop_radius = 0.45
            self.three_point_radius = 6.75

        # -----------------------------
        # Память предыдущего кадра
        # -----------------------------
        self.prev_ball_x: Optional[float] = None
        self.prev_ball_y: Optional[float] = None

        # Ограничение на "телепортацию"
        self.max_delta = 12.0  # метров за кадр (нереалистично больше)

    # ============================================================
    # MAIN EVENT ANALYSIS
    # ============================================================

    def analyze_ball_movement(self, ball_x: float, ball_y: float) -> Optional[Dict[str, Any]]:
        """
        Проверяет траекторию движения снаряда на пересечение ключевых линий.
        Возвращает словарь события или None.
        """

        # -----------------------------
        # Защита от NaN / inf
        # -----------------------------
        if not self._valid(ball_x) or not self._valid(ball_y):
            return None

        # -----------------------------
        # Первый кадр
        # -----------------------------
        if self.prev_ball_x is None:
            self.prev_ball_x = ball_x
            self.prev_ball_y = ball_y
            return None

        # -----------------------------
        # Анти‑телепортация
        # -----------------------------
        if self._is_teleport(ball_x, ball_y):
            logger.warning("[EventDetector] Игнорируем телепортацию координат.")
            self.prev_ball_x = ball_x
            self.prev_ball_y = ball_y
            return None

        event = None

        # ============================================================
        # FOOTBALL EVENTS
        # ============================================================
        if self.sport == "football":
            event = self._detect_football_events(ball_x, ball_y)

        # ============================================================
        # HOCKEY EVENTS
        # ============================================================
        elif self.sport == "hockey":
            event = self._detect_hockey_events(ball_x, ball_y)

        # ============================================================
        # BASKETBALL EVENTS (заготовка)
        # ============================================================
        elif self.sport == "basketball":
            event = self._detect_basketball_events(ball_x, ball_y)

        # -----------------------------
        # Обновляем память
        # -----------------------------
        self.prev_ball_x = ball_x
        self.prev_ball_y = ball_y

        if event:
            logger.info(f"[AI Event Extracted] {event['event_type']} | {event['details']}")

        return event

    # ============================================================
    # FOOTBALL
    # ============================================================

    def _detect_football_events(self, x: float, y: float) -> Optional[Dict[str, Any]]:
        event = None

        # Гол в левые ворота
        if self._crossed(self.prev_ball_x, x, self.goal_line_left):
            if self.goal_y_top <= y <= self.goal_y_bottom:
                event = self._make_event("GOAL_TEAM_B", f"Гол в левые ворота (Y={y:.2f})", x, y)

        # Гол в правые ворота
        elif self._crossed(self.prev_ball_x, x, self.goal_line_right):
            if self.goal_y_top <= y <= self.goal_y_bottom:
                event = self._make_event("GOAL_TEAM_A", f"Гол в правые ворота (Y={y:.2f})", x, y)

        # Аут
        elif y <= self.field_y_min or y >= self.field_y_max:
            if 0.0 < x < 105.0:
                event = self._make_event("OUT_OF_BOUNDS", f"Мяч покинул поле (X={x:.2f})", x, y)

        return event

    # ============================================================
    # HOCKEY
    # ============================================================

    def _detect_hockey_events(self, x: float, y: float) -> Optional[Dict[str, Any]]:
        event = None

        # Гол в левые ворота
        if self._crossed(self.prev_ball_x, x, self.goal_line_left):
            if self.goal_y_top <= y <= self.goal_y_bottom:
                event = self._make_event("GOAL_TEAM_B", f"Гол в левые ворота (Y={y:.2f})", x, y)

        # Гол в правые ворота
        elif self._crossed(self.prev_ball_x, x, self.goal_line_right):
            if self.goal_y_top <= y <= self.goal_y_bottom:
                event = self._make_event("GOAL_TEAM_A", f"Гол в правые ворота (Y={y:.2f})", x, y)

        # Вылет шайбы
        elif y <= self.field_y_min or y >= self.field_y_max:
            event = self._make_event("PUCK_OUT", f"Шайба покинула площадку (X={x:.2f})", x, y)

        return event

    # ============================================================
    # BASKETBALL (заготовка)
    # ============================================================

    def _detect_basketball_events(self, x: float, y: float) -> Optional[Dict[str, Any]]:
        # Попадание в кольцо
        dist_to_hoop = math.sqrt((x - self.hoop_x) ** 2 + (y - self.hoop_y) ** 2)
        if dist_to_hoop <= self.hoop_radius:
            return self._make_event("BASKET", "Попадание в кольцо", x, y)

        # За трехочковую дугу
        if dist_to_hoop >= self.three_point_radius:
            return self._make_event("THREE_POINT_ZONE", "Игрок за трехочковой дугой", x, y)

        return None

    # ============================================================
    # HELPERS
    # ============================================================

    @staticmethod
    def _valid(v: float) -> bool:
        return isinstance(v, (int, float)) and not math.isnan(v) and not math.isinf(v)

    def _is_teleport(self, x: float, y: float) -> bool:
        dx = abs(x - self.prev_ball_x)
        dy = abs(y - self.prev_ball_y)
        return dx > self.max_delta or dy > self.max_delta

    @staticmethod
    def _crossed(prev_x: float, curr_x: float, line_x: float) -> bool:
        return (prev_x < line_x <= curr_x) or (prev_x > line_x >= curr_x)

    @staticmethod
    def _make_event(event_type: str, details: str, x: float, y: float) -> Dict[str, Any]:
        return {
            "event_type": event_type,
            "details": details,
            "x": round(x, 3),
            "y": round(y, 3),
            "timestamp_ms": int(time.time() * 1000)
        }
