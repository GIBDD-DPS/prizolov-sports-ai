# ============================================
# Prizolov Sports AI - Main System Orchestrator
# Version: 3.01 (Initial Architecture Release)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at prizolov.ru
# ============================================

import asyncio
import logging
from typing import Dict, Any, Optional

from .line_generator import BroadLineGenerator
from ..agent_bridge.client import PrizolovAgentClient
from ..modules.football import FootballAnalyticsModule
from ..modules.hockey import HockeyAnalyticsModule
from ..modules.basketball import BasketballAnalyticsModule
from ..modules.miscellaneous import MiscellaneousSportsModule

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("PrizolovSportsAI.Orchestrator")

class PrizolovSportsOrchestrator:
    """Главный координатор системы: связывает ИИ-аналитику, видеопотоки и Agent OS"""

    def __init__(self, target_agent_host: str = "localhost:50051"):
        self.line_generator = BroadLineGenerator(default_margin=1.05) # Маржа букмекера 5%
        self.agent_client = PrizolovAgentClient(target_host=target_agent_host)
        
        # Активный в данный момент спортивный модуль
        self.active_module: Optional[Any] = None
        self.current_sport: Optional[str] = None
        self.match_id: Optional[str] = None
        self.is_initialized: bool = False

    async def initialize_match(self, match_id: str, sport: str) -> None:
        """Динамическая инициализация целевого спортивного модуля (Фабрика модулей)"""
        self.match_id = match_id
        self.current_sport = sport.lower()
        
        # Подключение к Agent OS через gRPC мост
        await self.agent_client.start()

        if self.current_sport == "football":
            self.active_module = FootballAnalyticsModule(match_id, self.line_generator)
        elif self.current_sport == "hockey":
            self.active_module = HockeyAnalyticsModule(match_id, self.line_generator)
        elif self.current_sport == "basketball":
            self.active_module = BasketballAnalyticsModule(match_id, self.line_generator)
        else:
            # Для всех остальных видов спорта инициализируем универсальный модуль «Разное»
            logger.info(f"Для вида спорта '{sport}' активирован универсальный адаптивный модуль.")
            self.active_module = MiscellaneousSportsModule(match_id, sport, self.line_generator)

        self.is_initialized = True
        logger.info(f"Матч {match_id} ({sport}) успешно оркестрован. Ожидание фреймов данных...")

    async def shutdown(self) -> None:
        """Корректное завершение работы оркестратора и деинициализация каналов связи"""
        self.is_initialized = False
        await self.agent_client.stop()
        logger.info("Главный оркестратор Sports AI успешно остановлен.")

    def update_official_protocol(self, protocol_data: Dict[str, Any]) -> None:
        """
        Обновляет официальный счет и статистику активного модуля на основе внешних данных.
        Вызывается при получении достоверных данных из судейского API или веб-панели.
        """
        if not self.is_initialized or not self.active_module:
            logger.warning("Попытка обновить протокол до инициализации матча.")
            return

        score_a = protocol_data.get("score_a", 0)
        score_b = protocol_data.get("score_b", 0)

        # Контекстное распределение параметров по типам модулей
        if self.current_sport == "football":
            self.active_module.set_match_state(
                score_a=score_a, score_b=score_b,
                corners_a=protocol_data.get("corners_a", 0),
                corners_b=protocol_data.get("corners_b", 0)
            )
        elif self.current_sport == "hockey":
            self.active_module.set_match_state(
                score_a=score_a, score_b=score_b,
                shots_a=protocol_data.get("shots_a", 0),
                shots_b=protocol_data.get("shots_b", 0)
            )
        elif self.current_sport == "basketball":
            self.active_module.set_match_state(
                score_a=score_a, score_b=score_b,
                fouls_a=protocol_data.get("fouls_a", 0),
                fouls_b=protocol_data.get("fouls_b", 0)
            )
        else:
            self.active_module.set_match_state(
                score_a=score_a, score_b=score_b,
                extra_a=protocol_data.get("extra_stat_a", 0),
                extra_b=protocol_data.get("extra_stat_b", 0)
            )

    async def process_cv_frame(self, 
                               tracking_data: Dict[str, Any], 
                               game_time_str: str, 
                               time_left_ratio: float,
                               elapsed_seconds: int = 0) -> bool:
        """
        Основной асинхронный метод конвейера. Обрабатывает входящий кадр от CV-модели,
        генерирует широкую линию и отправляет ее в gRPC-очередь Агента.
        """
        if not self.is_initialized or not self.active_module:
            logger.error("Оркестратор не инициализирован. Кадр отклонен.")
            return False

        try:
            # Передача параметров кадра в зависимости от требований модуля
            if self.current_sport == "basketball":
                analytics_package = self.active_module.process_frame_data(
                    tracking_data, game_time_str, time_left_ratio, elapsed_seconds
                )
            else:
                analytics_package = self.active_module.process_frame_data(
                    tracking_data, game_time_str, time_left_ratio
                )

            # Асинхронная отправка пакета в очередь gRPC клиента
            success = await self.agent_client.push_match_data(analytics_package)
            return success

        except Exception as e:
            logger.error(f"Критический сбой в конвейере обработки кадра оркестратора: {e}")
            return False
