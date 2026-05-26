# ============================================
# Prizolov Sports AI - Referee Severity Analytics
# Version: 5.02 (Minor Refactor & WP/Elementor Output Prep)
#
# CHANGELOG (5.01 → 5.02):
# - Удалены неиспользуемые импорты (os)
# - Уточнены типы и docstring-и
# - Упорядочено форматирование
# - Лёгкая чистка структуры без изменения логики
# - Подготовка структуры под API-вывод для WordPress Elementor
#
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production Discipline Line Calibration
# ============================================

import sys
import logging
from pathlib import Path
from typing import Dict, Any

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

logger = logging.getLogger("PrizolovSportsAI.RefereeAnalytics")


class RefereeSeverityAnalytics:
    """
    Процессор пре-матч скоринга и live-калибровки строгости судейских бригад.
    Готов к сериализации в JSON для API-слоя WordPress Elementor.
    """

    def __init__(self) -> None:
        self.referee_name: str = "Unknown"

        # Исторические показатели арбитра (по умолчанию — среднее по лиге)
        self.avg_cards_per_match: float = 4.0
        self.avg_penalties_per_match: float = 0.25

        # Индекс строгости (1.0 = средний судья)
        self.severity_index: float = 1.0

        # Флаг загрузки профиля
        self.is_profile_loaded: bool = False

    def load_referee_profile(self, profile_data: Dict[str, Any]) -> None:
        """
        Загружает исторический профиль судьи из пре-матч фидов спортивной статистики.

        Args:
            profile_data: словарь с данными судьи.
        """
        self.referee_name = profile_data.get("name", "Unknown")
        self.avg_cards_per_match = float(profile_data.get("avg_cards", 4.0))
        self.avg_penalties_per_match = float(profile_data.get("avg_penalties", 0.25))

        # Медиана лиги по карточкам
        league_median_cards = 4.0

        # Индекс строгости
        self.severity_index = float(self.avg_cards_per_match / league_median_cards)

        # Ограничение диапазона
        self.severity_index = max(min(self.severity_index, 1.45), 0.65)

        self.is_profile_loaded = True

        logger.info(
            f"[Referee Scoring] Загружен профиль арбитра: {self.referee_name} | "
            f"Ср. карточек: {self.avg_cards_per_match} | "
            f"Индекс строгости: {self.severity_index:.2f}"
        )

    def calibrate_discipline_intensity(self, base_discipline_lambda: float) -> float:
        """
        Модифицирует стартовую интенсивность Пуассоновского генератора карточек/удалений.

        Args:
            base_discipline_lambda: базовая интенсивность.

        Returns:
            Откалиброванная интенсивность.
        """
        if not self.is_profile_loaded:
            return base_discipline_lambda

        calibrated_lambda = base_discipline_lambda * self.severity_index

        logger.info(
            f"[Referee Scoring] Дисциплинарная лямбда откалибрована строгостью судьи: "
            f"{base_discipline_lambda} -> {calibrated_lambda:.2f}"
        )

        return round(calibrated_lambda, 2)
