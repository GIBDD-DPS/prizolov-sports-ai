# ============================================
# Prizolov Sports AI - Pre-Match Context Integration
# Version: 4.02 (Minor Refactor & Cleanup)
#
# CHANGELOG (4.01 → 4.02):
# - Удалены неиспользуемые импорты
# - Уточнены типы и docstring-и
# - Упорядочено форматирование
# - Лёгкая чистка структуры без изменения логики
#
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at prizolov.ru
# ============================================

from typing import Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger("PrizolovSportsAI.PreMatchContext")


class PreMatchContextModule:
    """Модуль управления пре-матчевой аналитикой и базовыми силами команд."""

    def __init__(self) -> None:
        """
        Инициализация контейнера для хранения контекста матча.
        В продакшене данные подгружаются из внутренней БД или JSON-конфигов.
        """
        self.context_data: Dict[str, Any] = {}

    def load_match_context(self, match_id: str, sport: str) -> Dict[str, Any]:
        """
        Имитирует загрузку глубоких пре-матчевых метрик из базы данных prizolov.ru.
        Возвращает стартовые веса и имена команд для ИИ-моделей.

        Args:
            match_id: Уникальный идентификатор матча.
            sport: Вид спорта.

        Returns:
            Словарь с пре-матчевыми параметрами.
        """
        logger.info(f"Загрузка пре-матч контекста для события {match_id} ({sport})...")

        # Дефолтный контекст-пакет (фолбэк)
        default_context = {
            "match_id": match_id,
            "sport": sport,
            "team_name_a": "Team_A",
            "team_name_b": "Team_B",
            "prematch_lambda_a": 1.45,
            "prematch_lambda_b": 1.15,
            "motivation_factor_a": 1.0,
            "motivation_factor_b": 1.0,
            "has_key_injuries_a": False,
            "has_key_injuries_b": False,
        }

        # Тестовые ID для проверки боевой логики
        if "mcl_football" in match_id:
            default_context.update({
                "team_name_a": "Zenit",
                "team_name_b": "Spartak",
                "prematch_lambda_a": 1.85,
                "prematch_lambda_b": 1.20,
                "motivation_factor_a": 1.15,
            })
        elif "mcl_hockey" in match_id:
            default_context.update({
                "team_name_a": "CSKA",
                "team_name_b": "SKA",
                "prematch_lambda_a": 3.10,
                "prematch_lambda_b": 2.90,
            })

        self.context_data = default_context
        return self.context_data

    def get_calibrated_lambdas(self) -> Tuple[float, float]:
        """
        Возвращает адаптированные базовые интенсивности с учетом травм и мотивации.

        Returns:
            Кортеж (lambda_a, lambda_b)
        """
        if not self.context_data:
            return 1.2, 1.0

        base_a = self.context_data.get("prematch_lambda_a", 1.2)
        base_b = self.context_data.get("prematch_lambda_b", 1.0)

        # Штраф за ключевые травмы
        if self.context_data.get("has_key_injuries_a", False):
            base_a *= 0.85
        if self.context_data.get("has_key_injuries_b", False):
            base_b *= 0.85

        # Турнирная мотивация
        base_a *= self.context_data.get("motivation_factor_a", 1.0)
        base_b *= self.context_data.get("motivation_factor_b", 1.0)

        return float(base_a), float(base_b)
