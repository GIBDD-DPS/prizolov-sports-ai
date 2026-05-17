# ============================================
# Prizolov Sports AI - Miscellaneous Sports Module
# Version: 3.01 (Initial Architecture Release)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at prizolov.ru
# ============================================

import numpy as np
from typing import Dict, Any, List
from ..core.line_generator import BroadLineGenerator

class MiscellaneousSportsModule:
    """Универсальный ИИ-модуль для генерации лучших и выгодных линий на любые виды спорта"""

    def __init__(self, match_id: str, sport_name: str, line_generator: BroadLineGenerator):
        self.match_id = match_id
        self.sport_name = sport_name.lower()
        self.lg = line_generator
        
        # Текущее состояние игры
        self.current_score_a = 0
        self.current_score_b = 0
        self.extra_stat_a = 0  # Универсальный счетчик (например, эйсы в теннисе, фраги в CS)
        self.extra_stat_b = 0
        
        # Сила соперников по умолчанию (адаптируется live-сканером)
        self.strength_factor_a = 1.0
        self.strength_factor_b = 1.0
        
        # Коэффициент тренда / импульса игры (Momentum)
        self.momentum_factor = 0.0 # Положительный — перевес игрока А, отрицательный — Б

    def set_match_state(self, score_a: int, score_b: int, extra_a: int = 0, extra_b: int = 0) -> None:
        """Обновление live-счета для произвольного вида спорта"""
        self.current_score_a = score_a
        self.current_score_b = score_b
        self.extra_stat_a = extra_a
        self.extra_stat_b = extra_b

    def _determine_best_model(self) -> str:
        """Автоматически выбирает оптимальный математический движок под специфику спорта"""
        high_scoring_sports = ["volleyball", "table_tennis", "badminton", "cybersport_frags"]
        if any(s in self.sport_name for s in high_scoring_sports):
            return "high_score_normal"  # Нормальное распределение (много очков/фрагов)
        return "low_score_poisson"      # Пуассон (редкие события: геймы, сеты, карты)

    def process_frame_data(self, 
                           tracking_data: Dict[str, Any], 
                           game_time_str: str, 
                           time_left_ratio: float) -> Dict[str, Any]:
        """
        Главный цикл универсального модуля. Оценивает тренды live-активности,
        выбирает лучшую математическую модель и генерирует широкую выгодную линию.
        """
        # Анализ тренда (Momentum) на основе последних событий в кадре
        # Например, скорость набора очков или доминирование на экране за последние 30 секунд
        recent_dominance = tracking_data.get("recent_dominance_ratio", 0.5) # 0.0 до 1.0
        self.momentum_factor = (recent_dominance - 0.5) * 2.0 # Сдвиг в диапазон [-1.0, 1.0]

        # Адаптация силы сторон с учетом тренда доминирования
        live_strength_a = self.strength_factor_a * (1.0 + self.momentum_factor * 0.15)
        live_strength_b = self.strength_factor_b * (1.0 - self.momentum_factor * 0.15)

        model_type = self._determine_best_model()
        is_suspended = tracking_data.get("is_paused", False)

        # Генерация базовых маркеров в зависимости от выбранной оптимальной модели
        if model_type == "high_score_normal":
            # Имитируем темп для волейбола/киберспорта (среднее количество очков/фрагов в оставшееся время)
            estimated_total_pace = tracking_data.get("expected_total_events", 100)
            base_markets = self.lg.calculate_high_score_line(
                pace=estimated_total_pace,
                efficiency_a=live_strength_a / (live_strength_a + live_strength_b),
                efficiency_b=live_strength_b / (live_strength_a + live_strength_b),
                time_left_ratio=time_left_ratio,
                current_score_a=self.current_score_a,
                current_score_b=self.current_score_b
            )
        else:
            # Для тенниса/геймов используем Пуассоновское распределение
            base_markets = self.lg.calculate_poisson_line(
                lambda_team_a=live_strength_a * 2.0,
                lambda_team_b=live_strength_b * 2.0,
                time_left_ratio=time_left_ratio,
                current_score_a=self.current_score_a,
                current_score_b=self.current_score_b
            )

        # Формирование выгодной линии на статистику (активные спешлы)
        # Рассчитываем дополнительную статистику (например, Эйсы, Фраги или Удары) через Пуассона
        lambda_stat_a = tracking_data.get("base_stat_lambda_a", 1.5) * live_strength_a
        lambda_stat_b = tracking_data.get("base_stat_lambda_b", 1.5) * live_strength_b
        
        stat_markets = self.lg.calculate_poisson_line(
            lambda_team_a=lambda_stat_a,
            lambda_team_b=lambda_stat_b,
            time_left_ratio=time_left_ratio,
            current_score_a=self.extra_stat_a,
            current_score_b=self.extra_stat_b,
            max_goals_to_simulate=30
        )

        # Динамическое именование рынков статистики под конкретный вид спорта
        stat_name = tracking_data.get("extra_stat_name", "Statistic")
        active_specials = []
        for outcome in stat_markets["totals"]:
            m_name = outcome["market_name"].replace("TO", f"{stat_name} Total Over").replace("TU", f"{stat_name} Total Under")
            active_specials.append({
                "market_name": m_name,
                "odds": outcome["odds"],
                "is_suspended": is_suspended or outcome["is_suspended"]
            })

        if is_suspended:
            for m in base_markets["main_outcomes"]: m["is_suspended"] = True
            for t in base_markets["totals"]: t["is_suspended"] = True

        # Сборка универсального выходного пакета
        output_package = {
            "match_id": self.match_id,
            "sport": self.sport_name,
            "game_time": game_time_str,
            "ball_state": {
                "x": tracking_data.get("object_x", 0.0),
                "y": tracking_data.get("object_y", 0.0),
                "vx": self.momentum_factor, # Передаем фактор импульса игры в векторе для Агента
                "vy": 0.0,
                "last_touch_id": tracking_data.get("last_active_player_id", -1)
            },
            "metrics": {
                "possession_a": round(max(min(recent_dominance * 100.0, 95.0), 5.0), 1),
                "possession_b": 0.0,
                "xg_a": tracking_data.get("performance_index_a", 0.0), # Индекс перформанса вместо xG
                "xg_b": tracking_data.get("performance_index_b", 0.0),
                "dangerous_attacks_a": tracking_data.get("attacks_count_a", 0),
                "dangerous_attacks_b": tracking_data.get("attacks_count_b", 0)
            },
            "line_data": {
                "main_outcomes": base_markets["main_outcomes"],
                "totals": base_markets["totals"],
                "handicaps": [],
                "active_specials": active_specials
            }
        }

        output_package["metrics"]["possession_b"] = round(100.0 - output_package["metrics"]["possession_a"], 1)

        return output_package
