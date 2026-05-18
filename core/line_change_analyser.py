# ============================================
# Prizolov Sports AI - Line Change Analytics
# Version: 5.01 (Initial Architecture Release)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Dynamic Team Strength Calibration
# ============================================

import sys
import os
from pathlib import Path

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import logging
from typing import Dict, Any, List, Set

logger = logging.getLogger("PrizolovSportsAI.LineChange")

class LineChangeAnalyser:
    """ИИ-процессор фиксации смены звеньев и расчета динамического индекса силы состава"""

    def __init__(self, sport: str):
        self.sport = sport.lower()
        
        # Рейтинг ценности игроков по номерам джерси (загружается из пре-матч контекста)
        # Структура: {номер_джерси: вес_игрока_от_0.5_до_1.5} (1.0 — средний уровень)
        self.player_weight_map_a: Dict[str, float] = {}
        self.player_weight_map_b: Dict[str, float] = {}
        
        # Текущий зафиксированный состав игроков на площадке
        self.current_floor_players_a: Set[str] = set()
        self.current_floor_players_b: Set[str] = set()

    def load_player_weights(self, weights_a: Dict[str, float], weights_b: Dict[str, float]) -> None:
        """Загружает персональные рейтинги эффективности игроков"""
        self.player_weight_map_a = weights_a
        self.player_weight_map_b = weights_b
        logger.info(f"[Line Change] Успешно загружен профиль ценности игроков для {self.sport.upper()}")

    def update_observed_players(self, observed_numbers_a: List[str], observed_numbers_b: List[str]) -> Tuple[float, float]:
        """
        Принимает списки распознанных OCR-номеров на джерси игроков текущего кадра.
        Рассчитывает текущий индекс силы состава (Line Strength Index) для Команды А и Б.
        """
        # Обновляем память состава, если уверенно распознано более 2-х игроков (фильтрация шумов OCR)
        if len(observed_numbers_a) >= 2:
            self.current_floor_players_a = set(observed_numbers_a)
        if len(observed_numbers_b) >= 2:
            self.current_floor_players_b = set(observed_numbers_b)

        # Функция расчета коэффициента силы
        def _calculate_index(floor_players: Set[str], weight_map: Dict[str, float]) -> float:
            if not floor_players:
                return 1.0 # Фолбэк на стандартную силу, если номера не распознаны
            
            total_weight = 0.0
            counted_players = 0
            
            for num in floor_players:
                # Берем вес игрока из карты, либо 1.0 для среднего спортсмена
                total_weight += weight_map.get(num, 1.0)
                counted_players += 1
                
            return float(total_weight / counted_players)

        index_a = _calculate_index(self.current_floor_players_a, self.player_weight_map_a)
        index_b = _calculate_index(self.current_floor_players_b, self.player_weight_map_b)

        # Если зафиксировано сильное падение индекса (вышел глубокий резерв), логируем событие
        if index_a < 0.85:
            logger.info(f"[Line Change Alert] У Команды А на поле вышло ослабленное звено (Индекс: {index_a:.2f})")
        if index_b < 0.85:
            logger.info(f"[Line Change Alert] У Команды Б на поле вышло ослабленное звено (Индекс: {index_b:.2f})")

        return round(index_a, 2), round(index_b, 2)
