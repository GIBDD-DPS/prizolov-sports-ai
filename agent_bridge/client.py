# ============================================
# Prizolov Sports AI - Agent OS Async Bridge Client
# Version: 3.02 (Absolute Cloud Imports Fix)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at prizolov.ru
# ============================================

import asyncio
import logging
import time
import sys
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, Optional

import grpc

# Гарантируем корректный поиск скомпилированных Protobuf файлов в Amvera
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Абсолютные импорты сгенерированных gRPC классов
import prizolov_agent_pb2
import prizolov_agent_pb2_grpc

# Настройка системного логирования для мониторинга на prizolov.ru
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("PrizolovSportsAI.Bridge")

class PrizolovAgentClient:
    """Асинхронный высокопроизводительный клиент для стриминга спортивной линии в Agent OS"""
    
    def __init__(self, target_host: str = "localhost:50051"):
        self.target_host = target_host
        self.channel: Optional[grpc.aio.Channel] = None
        self.stub: Optional[prizolov_agent_pb2_grpc.SportsAnalyticServiceStub] = None
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=1000) # Буфер пакетов для отправки
        self.is_running: bool = False
        
    async def start(self) -> None:
        """Запуск клиента и инициализация gRPC соединения"""
        self.is_running = True
        # Оптимизация gRPC канала для минимизации задержек и поддержания соединения (KeepAlive)
        channel_options = [
            ('grpc.keepalive_time_ms', 10000),
            ('grpc.keepalive_timeout_ms', 5000),
            ('grpc.http2.max_pings_without_data', 0),
            ('grpc.http2.min_time_between_pings_ms', 10000)
        ]
        
        self.channel = grpc.aio.insecure_channel(self.target_host, options=channel_options)
        self.stub = prizolov_agent_pb2_grpc.SportsAnalyticServiceStub(self.channel)
        
        # Запуск фоновой задачи непрерывной отправки данных
        asyncio.create_task(self._stream_worker())
        logger.info(f"gRPC мост инициализирован для подключения к Agent OS на {self.target_host}")

    async def stop(self) -> None:
        """Корректная остановка клиента с закрытием соединений"""
        self.is_running = False
        if self.channel:
            await self.channel.close()
            logger.info("gRPC канал связи с Agent OS успешно закрыт.")

    async def push_match_data(self, raw_data: Dict[str, Any]) -> bool:
        """
        Принимает сырые данные аналитики от спортивных модулей, 
        валидирует и помещает в очередь на отправку.
        """
        try:
            # Маппинг строкового типа спорта в Enum Protobuf
            sport_mapping = {
                "football": prizolov_agent_pb2.SPORT_FOOTBALL,
                "hockey": prizolov_agent_pb2.SPORT_HOCKEY,
                "basketball": prizolov_agent_pb2.SPORT_BASKETBALL
            }
            sport_enum = sport_mapping.get(raw_data.get("sport", "").lower(), prizolov_agent_pb2.SPORT_UNSPECIFIED)

            # Сборка структуры BallState
            b_state = raw_data.get("ball_state", {})
            ball_msg = prizolov_agent_pb2.BallState(
                position=prizolov_agent_pb2.Coordinate2D(x=b_state.get("x", 0.0), y=b_state.get("y", 0.0)),
                velocity_vector=prizolov_agent_pb2.Coordinate2D(x=b_state.get("vx", 0.0), y=b_state.get("vy", 0.0)),
                last_touch_player_id=b_state.get("last_touch_id", -1)
            )

            # Сборка AdvancedMetrics
            m_state = raw_data.get("metrics", {})
            metrics_msg = prizolov_agent_pb2.AdvancedMetrics(
                team_a_possession_pct=m_state.get("possession_a", 50.0),
                team_b_possession_pct=m_state.get("possession_b", 50.0),
                expected_goals_xg_a=m_state.get("xg_a", 0.0),
                expected_goals_xg_b=m_state.get("xg_b", 0.0),
                dangerous_attacks_a=m_state.get("dangerous_attacks_a", 0),
                dangerous_attacks_b=m_state.get("dangerous_attacks_b", 0)
            )

            # Вспомогательная функция для сборки исходов рынков широкой линии
            def build_outcomes(outcomes_list):
                return [prizolov_agent_pb2.MarketOutcome(
                    market_name=o["market_name"],
                    odds=float(o["odds"]),
                    is_suspended=o.get("is_suspended", False)
                ) for o in outcomes_list]

            line_state = raw_data.get("line_data", {})
            line_msg = prizolov_agent_pb2.BroadLine(
                main_outcomes=build_outcomes(line_state.get("main_outcomes", [])),
                totals=build_outcomes(line_state.get("totals", [])),
                handicaps=build_outcomes(line_state.get("handicaps", [])),
                active_specials=build_outcomes(line_state.get("active_specials", []))
            )

            # Формирование финального пакета данных
            package = prizolov_agent_pb2.MatchDataPackage(
                match_id=str(raw_data["match_id"]),
                sport=sport_enum,
                game_time=str(raw_data.get("game_time", "00:00")),
                timestamp_ms=int(time.time() * 1000),
                ball_state=ball_msg,
                metrics=metrics_msg,
                line_data=line_msg
            )

            # Помещаем пакет в очередь. Если очередь полна, отбрасываем старые фреймы
            try:
                self.queue.put_nowait(package)
                return True
            except asyncio.QueueFull:
                _ = self.queue.get_nowait() # Удаляем устаревший пакет
                self.queue.put_nowait(package)
                return True

        except Exception as e:
            logger.error(f"Ошибка сериализации данных матча: {e}")
            return False

    async def _packet_generator(self) -> AsyncGenerator[prizolov_agent_pb2.MatchDataPackage, None]:
        """Генератор пакетов из очереди для gRPC стрима"""
        while self.is_running:
            package = await self.queue.get()
            yield package
            self.queue.task_done()

    async def _stream_worker(self) -> None:
        """Фоновый воркер, управляющий жизненным циклом стрима и переподключениями"""
        retry_delay = 1.0
        while self.is_running:
            try:
                logger.info("Попытка установки активного стрима с Agent OS...")
                response = await self.stub.StreamMatchAnalytics(self._packet_generator())
                
                if response.is_success:
                    logger.info(f"Стрим завершен Agent OS успешно. Время обработки: {response.processed_timestamp_ms}")
                else:
                    logger.error(f"Agent OS отклонил пакеты: {response.error_message}")
                
                retry_delay = 1.0 # Сброс задержки при успешном подключении
                
            except grpc.RpcError as e:
                logger.warning(f"Потеря связи с Agent OS gRPC Server ({e.code()}). Повтор через {retry_delay}с...")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 60.0)
            except Exception as e:
                logger.error(f"Критический сбой в gRPC воркере: {e}")
                await asyncio.sleep(5)
