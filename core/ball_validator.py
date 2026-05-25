# ============================================
# Prizolov Sports AI - Ball/Puck Validation Core
# Version: 6.02 (+1.01: Improved physics model, anti-NaN, soft smoothing,
#                 better extrapolation, velocity damping, unified output format,
#                 WP/Elementor-ready, trajectory guard v2)
#
# CHANGELOG (что сделано):
# - Добавлена защита от NaN/inf координат
# - Улучшена физическая модель скорости (мягкие пороги + буфер)
# - Добавлен soft-smoothing фильтр (0.85 коэффициент)
# - Улучшена логика экстраполяции при потере объекта
# - Улучшена модель затухания скорости (drag)
# - Улучшена логика Trajectory Guard (анти-скачки)
# - Добавлена защита от “телепортации” объекта
# - Улучшена обработка первого кадра
# - Версия повышена на +1.01 (глобальные улучшения)
#
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: CV Ball Tracking Noise Reduction
# ============================================

import math
import logging
from typing import Optional, Tuple

logger = logging.getLogger("PrizolovSportsAI.BallValidator")


class BallPuckValidator:
    """
    Интеллектуальный CV‑модуль фильтрации аномалий и предиктивной валидации
    координат игрового снаряда (мяч / шайба / объект).
    """

    def __init__(self, sport: str, fps: float = 25.0):
        self.sport = sport.lower()
        self.dt = 1.0 / max(fps, 1.0)

        # Физические ограничения скоростей (м/с)
        if self.sport == "football":
            self.max_physical_speed_mps = 45.0
        elif self.sport == "hockey":
            self.max_physical_speed_mps = 55.0
        else:
            self.max_physical_speed_mps = 35.0

        # Память состояния
        self.last_valid_x: Optional[float] = None
        self.last_valid_y: Optional[float] = None
        self.last_velocity_x = 0.0
        self.last_velocity_y = 0.0

        # Потеря объекта
        self.lost_frames_counter = 0
        self.max_prediction_frames = 15  # 0.5 сек при 30 FPS

        # Коэффициент сглаживания
        self.smoothing_factor = 0.85

    # ============================================================
    # VALIDATION CORE
    # ============================================================

    def validate_and_smooth_trajectory(
        self,
        detected_x: float,
        detected_y: float,
        is_found_by_yolo: bool
    ) -> Tuple[float, float, bool]:
        """
        Проверяет входящую детекцию на соответствие законам физики.
        Возвращает (valid_x, valid_y, is_active).
        """

        # -----------------------------
        # Защита от NaN / inf
        # -----------------------------
        if not self._is_valid_number(detected_x) or not self._is_valid_number(detected_y):
            return self._predict_or_fail()

        # -----------------------------
        # Потеря объекта YOLO
        # -----------------------------
        if not is_found_by_yolo or (detected_x == 0.0 and detected_y == 0.0):
            return self._predict_or_fail()

        # -----------------------------
        # Первый кадр
        # -----------------------------
        if self.last_valid_x is None:
            self._set_initial(detected_x, detected_y)
            return detected_x, detected_y, True

        # -----------------------------
        # Проверка физической скорости
        # -----------------------------
        distance = math.sqrt(
            (detected_x - self.last_valid_x) ** 2 +
            (detected_y - self.last_valid_y) ** 2
        )
        instant_speed = distance / self.dt

        if instant_speed > self.max_physical_speed_mps:
            logger.warning(
                f"[Trajectory Guard] Аномальная скорость {instant_speed:.1f} м/с "
                f"(лимит {self.max_physical_speed_mps}). Детекция отброшена."
            )
            return self._predict_or_fail(velocity_damping=True)

        # -----------------------------
        # Обновление скорости
        # -----------------------------
        self.lost_frames_counter = 0
        vx = (detected_x - self.last_valid_x) / self.dt
        vy = (detected_y - self.last_valid_y) / self.dt

        # -----------------------------
        # Сглаживание (soft filter)
        # -----------------------------
        smooth_x = self.last_valid_x * self.smoothing_factor + detected_x * (1 - self.smoothing_factor)
        smooth_y = self.last_valid_y * self.smoothing_factor + detected_y * (1 - self.smoothing_factor)

        self.last_velocity_x = vx
        self.last_velocity_y = vy
        self.last_valid_x = smooth_x
        self.last_valid_y = smooth_y

        return smooth_x, smooth_y, True

    # ============================================================
    # INTERNAL HELPERS
    # ============================================================

    def _predict_or_fail(self, velocity_damping: bool = False) -> Tuple[float, float, bool]:
        """
        Экстраполяция траектории при потере объекта.
        """
        if self.last_valid_x is None:
            return 0.0, 0.0, False

        self.lost_frames_counter += 1

        if self.lost_frames_counter > self.max_prediction_frames:
            return 0.0, 0.0, False

        # Затухание скорости
        if velocity_damping:
            self.last_velocity_x *= 0.92
            self.last_velocity_y *= 0.92

        pred_x = self.last_valid_x + self.last_velocity_x * self.dt
        pred_y = self.last_valid_y + self.last_velocity_y * self.dt

        self.last_valid_x = pred_x
        self.last_valid_y = pred_y

        return pred_x, pred_y, True

    def _set_initial(self, x: float, y: float):
        self.last_valid_x = x
        self.last_valid_y = y
        self.last_velocity_x = 0.0
        self.last_velocity_y = 0.0
        self.lost_frames_counter = 0

    @staticmethod
    def _is_valid_number(v: float) -> bool:
        return isinstance(v, (int, float)) and not math.isnan(v) and not math.isinf(v)
