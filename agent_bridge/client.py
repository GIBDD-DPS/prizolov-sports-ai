# ============================================
# Prizolov Sports AI - Agent OS Async Bridge Client
# Version: 3.03 (Smart Batching Hub)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at prizolov.ru
# ============================================

import asyncio
import logging
import time
import sys
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, Optional, List

import grpc

# Гарантируем корректный поиск скомпилированных Protobuf файлов в Amvera
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

import prizolov_agent_pb2
import prizolov_agent_pb2_grpc

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("PrizolovSportsAI.Bridge")

class PrizolovAgentClient:
    """Асинхронный высокопроизводительный gRPC клиент с поддержкой Smart Batching и адаптивной дедупликации"""
    
    def __init__(self, target_host: str = "localhost:50051", epsilon_odds_diff: float = 0.015):
        self.target_host = target_host
        self.eps = epsilon_odds_diff
        
        self.channel: Optional[grpc.aio.Channel] = None
        self.stub: Optional[prizolov_agent_pb2_grpc.SportsAnalyticServiceStub] = None
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=2000)
        self.is_running: bool = False
        
        # Кэш последних отправленных рынков для транспортной дедупликации (защита от сетевого флуда)
        self.history_odds_cache: Dict[str, float] = {}
        
    async def start(self) -> None:
        """Запуск клиента и инициализация оптимизированного gRPC соединения"""
        self.is_running = True
        channel_options = [
            ('grpc.keepalive_time_ms', 10000),
            ('grpc.keepalive_timeout_ms', 5000),
            ('grpc.http2.max_pings_without_data', 0),
            ('grpc.http2.min_time_between_pings_ms', 10000),
            ('grpc.default_compression_algorithm', 2), # GZIP уплотнение трафика на уровне gRPC
            ('grpc.default_compression_level', 3)
        ]
        
        self.channel = grpc.aio.insecure_channel(self.target_host, options=channel_options)
        self.stub = prizolov_agent_pb2_grpc.SportsAnalyticServiceStub(self.channel)
        
        asyncio.create_task(self._stream_worker())
        logger.info(f"gRPC Smart-мост инициализирован для подключения к Agent OS на {self.target_host}")

    async def stop(self) -> None:
        """Корректная остановка клиента с закрытием соединений"""
        self.is_running = False
        if self.channel:
            await self.channel.close()
            logger.info("gRPC канал связи с Agent OS успешно закрыт.")

    def _should_filter_by_epsilon(self, package: prizolov_agent_pb2.MatchDataPackage) -> bool:
        """Проверяет, содержат ли новые букмекерские коэффициенты значимые live-изменения"""
        significant_change_detected = False
        
        # Лямбда-помощник для проверки векторов исходов в Protobuf структурах широкой линии
        def _check_market_list(outcomes):
            nonlocal significant_change_detected
            for o in outcomes:
                key = f"{package.match_id}:{o.market_name}"
                old_odds = self.history_odds_cache.get(key, 0.0)
                
                if abs(old_odds - o.odds) > self.eps or o.is_suspended:
                    self.history_odds_cache[key] = o.odds
                    significant_change_detected = True

        _check_market_list(package.line_data.main_outcomes)
        _check_market_list(package.line_data.totals)
        _check_market_list(package.line_data.handicaps)
        _check_market_list(package.line_data.active_specials)
        
        # Если это первый запуск или коэффициенты прыгнули выше эпсилон-порога
        if not self.history_odds_cache or significant_change_detected:
            return False # Не фильтруем, пакет боевой
            
        return True # Изменения ничтожны, пакет можно отбросить для экономии трафика

    async def push_match_data(self, raw_data: Dict[str, Any]) -> bool:
        """Валидирует, собирает, упаковывает и отправляет данные в очередь gRPC стрима"""
        try:
            sport_mapping = {
                "football": prizolov_agent_pb2.SPORT_FOOTBALL,
                "hockey": prizolov_agent_pb2.SPORT_HOCKEY,
                "basketball": prizolov_agent_pb2.SPORT_BASKETBALL
            }
            sport_enum = sport_mapping.get(raw_data.get("sport", "").lower(), prizolov_agent_pb2.SPORT_UNSPECIFIED)

            b_state = raw_data.get("ball_state", {})
            ball_msg = prizolov_agent_pb2.BallState(
                position=prizolov_agent_pb2.Coordinate2D(x=b_state.get("x", 0.0), y=b_state.get("y", 0.0)),
                velocity_vector=prizolov_agent_pb2.Coordinate2D(x=b_state.get("vx", 0.0), y=b_state.get("vy", 0.0)),
                last_touch_player_id=b_state.get("last_touch_id", -1)
            )

            m_state = raw_data.get("metrics", {})
            metrics_msg = prizolov_agent_pb2.AdvancedMetrics(
                team_a_possession_pct=m_state.get("possession_a", 50.0),
                team_b_possession_pct=m_state.get("possession_b", 50.0),
                expected_goals_xg_a=m_state.get("xg_a", 0.0),
                expected_goals_xg_b=m_state.get("xg_b", 0.0),
                dangerous_attacks_a=m_state.get("dangerous_attacks_a", 0),
                dangerous_attacks_b=m_state.get("dangerous_attacks_b", 0)
            )

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

            package = prizolov_agent_pb2.MatchDataPackage(
                match_id=str(raw_data["match_id"]),
                sport=sport_enum,
                game_time=str(raw_data.get("game_time", "00:00")),
                timestamp_ms=int(time.time() * 1000),
                ball_state=ball_msg,
                metrics=metrics_msg,
                line_data=line_msg
            )

            # Новое: Адаптивная смарт-дедупликация на транспортном уровне gRPC-клиента
            if self._should_filter_by_epsilon(package):
                return True

            try:
                self.queue.put_nowait(package)
                return True
            except asyncio.QueueFull:
                _ = self.queue.get_nowait()
                self.queue.put_nowait(package)
                return True

        except Exception as e:
            logger.error(f"Ошибка сериализации данных матча: {e}")
            return False

    async def _packet_generator(self) -> AsyncGenerator[prizolov_agent_pb2.MatchDataPackage, None]:
        """Генератор пакетов из высокоскоростной очереди для gRPC стрима"""
        while self.is_running:
            package = await self.queue.get()
            yield package
            self.queue.task_done()

    async def _stream_worker(self) -> None:
        """Фоновый воркер, управляющий жизненным циклом стрима, батчингом и переподключениями"""
        retry_delay = 1.0
        while self.is_running:
            try:
                logger.info("Попытка установки активного стрима с Agent OS...")
                response = await self.stub.StreamMatchAnalytics(self._packet_generator())
                
                if response.is_success:
                    logger.info(f"Стрим завершен Agent OS успешно. Время обработки: {response.processed_timestamp_ms}")
                else:
                    logger.error(f"Agent OS отклонил пакеты: {response.error_message}")
                
                retry_delay = 1.0
                
            except grpc.RpcError as e:
                logger.warning(f"Потеря связи с Agent OS gRPC Server ({e.code()}). Повтор через {retry_delay}с...")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 60.0)
            except Exception as e:
                logger.error(f"Критический сбой в gRPC воркере: {e}")
                await asyncio.sleep(5)
