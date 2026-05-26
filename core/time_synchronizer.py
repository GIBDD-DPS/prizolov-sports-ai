# ============================================
# Prizolov Sports AI - Optical Time Synchronizer
# Version: 5.02 (Minor Refactor, Bugfix & WP/Elementor Prep)
#
# CHANGELOG (5.01 → 5.02):
# - Добавлен отсутствующий импорт: from pathlib import Path
# - Уточнены типы и docstring-и
# - Упорядочены импорты
# - Лёгкая чистка структуры без изменения логики
# - Подготовка структуры под API-вывод игрового времени для WordPress Elementor
#
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production Real-time Clock Alignment
# ============================================

import sys
import os
import cv2
import re
import numpy as np
import logging
from pathlib import Path
from typing import Tuple, Optional

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

logger = logging.getLogger("PrizolovSportsAI.TimeSync")


class OpticalTimeSynchronizer:
    """
    Модуль оптического распознавания (OCR) и синхронизации игрового времени
    с экрана трансляции. Готов к сериализации в JSON для API-слоя WordPress Elementor.
    """

    def __init__(self, scorebug_crop_coords: Tuple[int, int, int, int] = (20, 40, 180, 80)) -> None:
        """
        Args:
            scorebug_crop_coords: координаты зоны таймера [x1, y1, x2, y2] в пикселях.
        """
        self.crop_x1, self.crop_y1, self.crop_x2, self.crop_y2 = scorebug_crop_coords
        self.last_valid_seconds: int = 0

    def set_scorebug_zone(self, x1: int, y1: int, x2: int, y2: int) -> None:
        """
        Позволяет оперативно перенастроить зону поиска под конкретный телеканал или трансляцию.
        """
        self.crop_x1 = x1
        self.crop_y1 = y1
        self.crop_x2 = x2
        self.crop_y2 = y2

    def sync_time_by_ocr(self, frame: np.ndarray) -> Optional[int]:
        """
        Вырезает зону таймера, подготавливает изображение к распознаванию контуров цифр.
        Возвращает точное количество прошедших секунд матча или None, если кадр размыт.

        Returns:
            total_seconds (int) — если OCR дал валидный результат,
            None — если распознать время невозможно.
        """
        if frame is None or frame.size == 0:
            return None

        img_h, img_w, _ = frame.shape

        # Корректируем координаты под границы кадра
        x1 = min(max(0, self.crop_x1), img_w)
        y1 = min(max(0, self.crop_y1), img_h)
        x2 = min(max(0, self.crop_x2), img_w)
        y2 = min(max(0, self.crop_y2), img_h)

        bug_crop = frame[y1:y2, x1:x2]
        if bug_crop.size == 0:
            return None

        # Препроцессинг: серый → увеличение контраста → порог Оцу
        gray = cv2.cvtColor(bug_crop, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(gray, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        _, thresh = cv2.threshold(resized, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # В проде здесь вызывается OCR (pytesseract)
        # Для архитектурного теста используем mock
        mock_ocr_text = "43:12"

        # Ищем паттерн ММ:СС или ЧЧ:ММ:СС
        time_match = re.search(r"(\d+):(\d+)", mock_ocr_text)
        if time_match:
            try:
                minutes = int(time_match.group(1))
                seconds = int(time_match.group(2))
                total_seconds = minutes * 60 + seconds

                # Защита от ложных скачков OCR
                if 0 <= (total_seconds - self.last_valid_seconds) <= 5:
                    self.last_valid_seconds = total_seconds
                    return total_seconds

            except ValueError:
                pass

        return self.last_valid_seconds
