# ============================================
# Prizolov Sports AI - Referee Severity Analytics
# Version: 5.01 (Initial Architecture Release)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production Discipline Line Calibration
# ============================================

import sys
import os
import logging
from pathlib import Path
from typing import Dict, Any

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

logger = logging.getLogger("PrizolovSportsAI.RefereeAnalytics")

class RefereeSeverityAnalytics:
    """Процессор пре-матч скоринга и live-калибровки строгости судейских бригад"""

    def __init__(self):
        self.referee_name = "Unknown"
        # Средние исторические показатели арбитра (дефолт равен среднему по лиге)
        self.avg_cards_per_match = 4.0
        self.avg_penalties_per_match = 0.25
        self.severity_index = 1.0
        self.is_profile_loaded = False

    def load_referee_profile(self, profile_data: Dict[str, Any]) -> None:
        """Загружает исторический профиль судьи из пре-матч фидов спортивной статистики"""
        self.referee_name = profile_data.get("name", "Unknown")
        self.avg_cards_per_match = float(profile_data.get("avg_cards", 4.0))
        self.avg_penalties_per_match = float(profile_data.get("avg_penalties", 0.25))
        
        # Расчет индекса строгости относительно медианы чемпионата (медиана = 4.0 карточки за игру)
        league_median_cards = 4.0
        self.severity_index = float(self.avg_cards_per_match / league_median_cards)
        # Ограничиваем индекс разумными рамками, чтобы избежать экстремальных перекосов линии
        self.severity_index = max(min(self.severity_index, 1.45), 0.65)
        
        self.is_profile_loaded = True
        logger.info(
            f"[Referee Scoring] Загружен профиль арбитра: {self.referee_name} | "
            f"Ср. карточек: {self.avg_cards_per_match} | Индекс строгости: {self.severity_index:.2f}"
        )

    def calibrate_discipline_intensity(self, base_discipline_lambda: float) -> float:
        """
        Модифицирует стартовую интенсивность Пуассоновского генератора карточек/удалений.
        Вызывается оркестратором при инициализации дисциплинарных маркетов.
        """
        if not self.is_profile_loaded:
            return base_discipline_lambda
            
        calibrated_lambda = base_discipline_lambda * self.severity_index
        logger.info(
            f"[Referee Scoring] Дисциплинарная лямбда откалибрована строгостью судьи: "
            f"{base_discipline_lambda} -> {calibrated_lambda:.2f}"
        )
        return round(calibrated_lambda, 2)
