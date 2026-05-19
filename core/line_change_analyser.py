# ============================================
# Prizolov Sports AI - Line Change Analyser
# Version: 5.02 (Strict Type Enforcement)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Dynamic Player Performance Mapping
# ============================================

import sys
import os
from pathlib import Path
# ИСПРАВЛЕНО: Добавлен обязательный импорт системы типов typing для ликвидации NameError
from typing import List, Dict, Any, Tuple, Optional

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

class LineChangeAnalyser:
    """Анализатор смен звеньев и персонального вклада игроков в интенсивность атак команды"""

    def __init__(self, sport: str):
        self.sport = sport.lower()
        self.player_weights_team_a: Dict[str, float] = {}
        self.player_weights_team_b: Dict[str, float] = {}
        self.current_active_players_a: List[str] = []
        self.current_active_players_b: List[str] = []

    def load_player_weights(self, weights_a: Dict[str, float], weights_b: Dict[str, float]) -> None:
        """Загружает индивидуальные веса влияния футболистов/хоккеистов из базы данных"""
        self.player_weights_team_a = weights_a
        self.player_weights_team_b = weights_b

    def update_observed_players(self, observed_numbers_a: List[str], observed_numbers_b: List[str]) -> Tuple[float, float]:
        """
        Вычисляет совокупный индекс силы текущего состава команд на поле.
        Возвращает [team_a_strength_index, team_b_strength_index].
        """
        if observed_numbers_a:
            self.current_active_players_a = observed_numbers_a
        if observed_numbers_b:
            self.current_active_players_b = observed_numbers_b

        # Расчет индекса силы для Команды А
        factor_a = 1.0
        if self.current_active_players_a:
            weights_sum_a = sum(self.player_weights_team_a.get(num, 1.0) for num in self.current_active_players_a)
            factor_a = weights_sum_a / len(self.current_active_players_a)

        # Расчет индекса силы для Команды Б
        factor_b = 1.0
        if self.current_active_players_b:
            weights_sum_b = sum(self.player_weights_team_b.get(num, 1.0) for num in self.current_active_players_b)
            factor_b = weights_sum_b / len(self.current_active_players_b)

        # Ограничиваем флуктуации индекса в пределах маржинальной безопасности (±30%)
        factor_a = max(min(factor_a, 1.30), 0.70)
        factor_b = max(min(factor_b, 1.30), 0.70)

        return round(factor_a, 2), round(factor_b, 2)
