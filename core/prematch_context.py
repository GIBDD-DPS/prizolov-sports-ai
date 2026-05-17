# ============================================
# Prizolov Sports AI - Pre-Match Context Integration
# Version: 4.01 (Initial Architecture Release)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at prizolov.ru
# ============================================

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger("PrizolovSportsAI.PreMatchContext")

class PreMatchContextModule:
    """Модуль управления пре-матчевой аналитикой и базовыми силами команд"""

    def __init__(self):
        # Базовая заглушка структуры хранения профилей команд
        # В проде данные подтягиваются из внутренней СУБД или JSON-конфигов матча
        self.context_data: Dict[str, Any] = {}

    def load_match_context(self, match_id: str, sport: str) -> Dict[str, Any]:
        """
        Имитирует загрузку глубоких пре-матчевых метрик из базы данных prizolov.ru.
        Возвращает стартовые веса и имена команд для ИИ-моделей.
        """
        logger.info(f"Загрузка пре-матч контекста для события {match_id} ({sport})...")
        
        # Дефолтный контекст-пакет (Фолбэк)
        default_context = {
            "match_id": match_id,
            "sport": sport,
            "team_name_a": "Team_A",
            "team_name_b": "Team_B",
            "prematch_lambda_a": 1.45,  # Историческая результативность хозяев
            "prematch_lambda_b": 1.15,  # Историческая результативность гостей
            "motivation_factor_a": 1.0, # Обычная мотивация
            "motivation_factor_b": 1.0,
            "has_key_injuries_a": False,
            "has_key_injuries_b": False
        }

        # Архитектурный маппинг тестовых ID для проверки боевой логики
        if "mcl_football" in match_id:
            default_context.update({
                "team_name_a": "Zenit",
                "team_name_b": "Spartak",
                "prematch_lambda_a": 1.85,  # Высокий атакующий потенциал дома
                "prematch_lambda_b": 1.20,
                "motivation_factor_a": 1.15, # Борьба за чемпионство
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

    def get_calibrated_lambdas(self) -> tuple[float, float]:
        """Возвращает адаптированные базовые интенсивности с учетом травм и мотивации"""
        if not self.context_data:
            return 1.2, 1.0

        base_a = self.context_data.get("prematch_lambda_a", 1.2)
        base_b = self.context_data.get("prematch_lambda_b", 1.0)

        # Применяем штраф к силе команды, если у нее есть ключевые травмы по пре-матч сводкам
        if self.context_data.get("has_key_injuries_a", False): base_a *= 0.85
        if self.context_data.get("has_key_injuries_b", False): base_b *= 0.85

        # Применяем множитель турнирной мотивации
        base_a *= self.context_data.get("motivation_factor_a", 1.0)
        base_b *= self.context_data.get("motivation_factor_b", 1.0)

        return float(base_a), float(base_b)
