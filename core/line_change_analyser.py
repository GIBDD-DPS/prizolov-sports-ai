# ============================================
# Prizolov Sports AI - Line Change Analyser
# Version: 6.03 (+1.01: stability clamp, NaN protection, 
#                 weighted averaging, safe player sets,
#                 unified style, WP-ready)
#
# CHANGELOG (что сделано):
# - Добавлена защита от NaN/inf в весах игроков
# - Улучшена логика усреднения (устойчивость к выбросам)
# - Добавлен stability clamp (анти-скачки при резкой смене звена)
# - Добавлена защита от пустых составов
# - Улучшена обработка отсутствующих игроков
# - Единый стиль с остальными модулями Prizolov Sports AI
# - Версия повышена на +1.01
#
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Dynamic Player Performance Mapping
# ============================================

from typing import List, Dict, Tuple
import math


class LineChangeAnalyser:
    """
    Анализатор смен звеньев и персонального вклада игроков
    в интенсивность атак команды.
    """

    def __init__(self, sport: str):
        self.sport = sport.lower()

        # Индивидуальные веса игроков
        self.player_weights_team_a: Dict[str, float] = {}
        self.player_weights_team_b: Dict[str, float] = {}

        # Текущие составы на площадке
        self.current_active_players_a: List[str] = []
        self.current_active_players_b: List[str] = []

        # Последние значения для анти‑скачков
        self.last_factor_a = 1.0
        self.last_factor_b = 1.0

        # Коэффициент сглаживания (anti-jitter)
        self.smoothing = 0.25

    # ============================================================
    # LOAD WEIGHTS
    # ============================================================

    def load_player_weights(self, weights_a: Dict[str, float], weights_b: Dict[str, float]) -> None:
        """Загружает индивидуальные веса влияния игроков."""
        self.player_weights_team_a = self._sanitize_weights(weights_a)
        self.player_weights_team_b = self._sanitize_weights(weights_b)

    @staticmethod
    def _sanitize_weights(weights: Dict[str, float]) -> Dict[str, float]:
        """Удаляет NaN/inf и заменяет некорректные значения на 1.0."""
        clean = {}
        for k, v in weights.items():
            if isinstance(v, (int, float)) and not math.isnan(v) and not math.isinf(v):
                clean[k] = float(v)
            else:
                clean[k] = 1.0
        return clean

    # ============================================================
    # UPDATE ACTIVE PLAYERS
    # ============================================================

    def update_observed_players(
        self,
        observed_numbers_a: List[str],
        observed_numbers_b: List[str]
    ) -> Tuple[float, float]:
        """
        Вычисляет совокупный индекс силы текущего состава команд.
        Возвращает (team_a_strength_index, team_b_strength_index).
        """

        if observed_numbers_a:
            self.current_active_players_a = observed_numbers_a

        if observed_numbers_b:
            self.current_active_players_b = observed_numbers_b

        # -----------------------------
        # Команда A
        # -----------------------------
        factor_a = self._compute_team_factor(
            self.current_active_players_a,
            self.player_weights_team_a
        )

        # -----------------------------
        # Команда B
        # -----------------------------
        factor_b = self._compute_team_factor(
            self.current_active_players_b,
            self.player_weights_team_b
        )

        # -----------------------------
        # Сглаживание (anti-jitter)
        # -----------------------------
        factor_a = self._smooth(self.last_factor_a, factor_a)
        factor_b = self._smooth(self.last_factor_b, factor_b)

        self.last_factor_a = factor_a
        self.last_factor_b = factor_b

        return round(factor_a, 2), round(factor_b, 2)

    # ============================================================
    # INTERNAL HELPERS
    # ============================================================

    def _compute_team_factor(self, players: List[str], weights: Dict[str, float]) -> float:
        """Усредняет веса игроков с защитой от выбросов."""
        if not players:
            return 1.0

        values = [weights.get(p, 1.0) for p in players]

        # Ограничиваем экстремальные значения
        values = [max(min(v, 2.0), 0.3) for v in values]

        avg = sum(values) / len(values)

        # Ограничиваем итоговый индекс в безопасном диапазоне
        return max(min(avg, 1.30), 0.70)

    def _smooth(self, prev: float, new: float) -> float:
        """Сглаживание резких скачков."""
        return prev * (1 - self.smoothing) + new * self.smoothing
