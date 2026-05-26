# ============================================
# Prizolov Sports AI - Pre-Match Feed Integrator
# Version: 5.02 (Minor Refactor & Cleanup)
#
# CHANGELOG (5.01 → 5.02):
# - Удалены неиспользуемые импорты (os)
# - Уточнены типы и docstring-и
# - Упорядочены импорты
# - Улучшено форматирование
# - Лёгкая чистка структуры без изменения логики
#
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at cloud.amvera.ru
# ============================================

import sys
from pathlib import Path
import httpx
import logging
from typing import Dict, Any, Tuple

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

logger = logging.getLogger("PrizolovSportsAI.PreMatchFeed")


class PreMatchFeedIntegrator:
    """Асинхронный модуль сбора предматчевой статистики из внешних API для автокалибровки ИИ."""

    def __init__(self, api_key: str = "demo_key") -> None:
        """
        Args:
            api_key: Ключ доступа к внешнему статистическому API.
        """
        self.api_key = api_key
        self.base_url = "https://prizolov.ru"

    async def fetch_team_form_metrics(self, team_name: str, sport: str) -> Dict[str, Any]:
        """
        Запрашивает у статистического API метрики результативности команды за последние 10 матчей.
        В случае сбоя сети возвращает безопасные дефолтные значения.

        Args:
            team_name: Название команды.
            sport: Вид спорта.

        Returns:
            Словарь с метриками формы команды.
        """
        url = f"{self.base_url}/{sport}/teams/{team_name}/form"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "avg_goals_scored": float(data.get("avg_scored", 1.2)),
                        "avg_goals_conceded": float(data.get("avg_conceded", 1.1)),
                        "motivation_index": float(data.get("motivation", 1.0)),
                        "has_injuries": bool(data.get("key_injuries", False)),
                    }

        except Exception as e:
            logger.error(
                f"Не удалось получить API фид для команды {team_name}: {e}. "
                f"Фолбэк на базовые веса."
            )

        # Защитный фолбэк
        return {
            "avg_goals_scored": 1.2,
            "avg_goals_conceded": 1.1,
            "motivation_index": 1.0,
            "has_injuries": False,
        }

    async def calibrate_match_lambdas(
        self, match_id: str, team_a: str, team_b: str, sport: str
    ) -> Tuple[float, float]:
        """
        Агрегирует пре-матч метрики обеих команд и вычисляет стартовые значения
        лямбда (интенсивности) для Пуассоновского/Нормального генератора.

        Args:
            match_id: ID матча.
            team_a: Название команды A.
            team_b: Название команды B.
            sport: Вид спорта.

        Returns:
            Кортеж (lambda_a, lambda_b).
        """
        logger.info(
            f"[API Feed] Запущена автокалибровка сил для матча {match_id} "
            f"({team_a} vs {team_b})..."
        )

        # Асинхронные запросы
        task_a = self.fetch_team_form_metrics(team_a, sport)
        task_b = self.fetch_team_form_metrics(team_b, sport)
        stats_a, stats_b = await asyncio.gather(task_a, task_b)

        # Базовая интенсивность атаки
        lambda_a = (stats_a["avg_goals_scored"] + stats_b["avg_goals_conceded"]) / 2.0
        lambda_b = (stats_b["avg_goals_scored"] + stats_a["avg_goals_conceded"]) / 2.0

        # Корректировка на травмы
        if stats_a["has_injuries"]:
            lambda_a *= 0.88
        if stats_b["has_injuries"]:
            lambda_b *= 0.88

        # Корректировка на мотивацию
        lambda_a *= stats_a["motivation_index"]
        lambda_b *= stats_b["motivation_index"]

        logger.info(
            f"[API Feed] Автокалибровка завершена. "
            f"Lambda A: {lambda_a:.2f}, Lambda B: {lambda_b:.2f}"
        )

        return round(lambda_a, 2), round(lambda_b, 2)
