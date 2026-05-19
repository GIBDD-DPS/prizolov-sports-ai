# ============================================
# Prizolov Sports AI - Core Orchestrator
# Version: 3.05 (+1.01: Real Football Analytics Integration & Pipeline Refactoring)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at cloud.amvera.ru
# ============================================

import os
import asyncio
import logging
import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger("PrizolovSportsAI.Orchestrator")

# Безопасный импорт gRPC-клиента
try:
    from agent_bridge.prizolov_agent_pb2_grpc import PrizolovAgentStub
    from agent_bridge.prizolov_agent_pb2 import LineRequest
    import grpc
    HAS_GRPC = True
except ImportError:
    HAS_GRPC = False
    logger.warning("⚠️ gRPC modules not found. Mock mode will be forced.")

# Безопасный импорт аналитического модуля
try:
    from modules.football import FootballAnalyticsModule
    HAS_FOOTBALL_ANALYTICS = True
except ImportError:
    try:
        from prizolov_sports_ai.modules.football import FootballAnalyticsModule
        HAS_FOOTBALL_ANALYTICS = True
    except ImportError:
        HAS_FOOTBALL_ANALYTICS = False
        logger.warning("⚠️ Football analytics module not found. Fallback to mock mode.")

class PrizolovSportsOrchestrator:
    def __init__(self, target_agent_host: str = "localhost:50051", mock_mode: bool = False):
        self.target_agent_host = target_agent_host
        self.mock_mode = mock_mode or not HAS_GRPC
        self.agent_client = None
        self.active_matches = {}
        self.line_cache = {}
        self.analytics_engine = None

        # Инициализация аналитического движка
        if HAS_FOOTBALL_ANALYTICS and not self.mock_mode:
            self.analytics_engine = FootballAnalyticsModule()
            logger.info("✅ Football Analytics Module loaded successfully")

        if not self.mock_mode:
            try:
                self.channel = grpc.insecure_channel(target_agent_host)
                self.agent_client = PrizolovAgentStub(self.channel)
                logger.info(f"✅ gRPC channel established to {target_agent_host}")
            except Exception as e:
                logger.error(f"❌ Failed to connect to Agent OS at {target_agent_host}: {e}")
                logger.info("🔄 Fallback: switching to MOCK MODE automatically")
                self.mock_mode = True

        if self.mock_mode or not self.analytics_engine:
            logger.info("🎭 Orchestrator running in MOCK/SAFE MODE. External calls are simulated.")

    async def initialize_match(self, match_id: str, sport: str = "football") -> None:
        self.active_matches[match_id] = {
            "sport": sport,
            "status": "initialized",
            "start_time": datetime.datetime.utcnow().isoformat(),
            "protocol": {"score_a": 0, "score_b": 0}
        }
        logger.info(f"📦 Match {match_id} initialized for {sport}")

    async def process_cv_frame(
        self,
        match_id: str,
        tracking_data: Dict[str, Any],
        game_time_str: str,
        time_left_ratio: float,
        elapsed_seconds: int
    ) -> None:
        if match_id not in self.active_matches:
            return

        # Эмуляция задержки обработки кадра
        await asyncio.sleep(0.01)
        
        dominance = tracking_data.get("recent_dominance_ratio", 0.5)
        
        # Генерация рекомендаций каждые 30 секунд игрового времени
        if elapsed_seconds % 30 == 0:
            await self._generate_and_broadcast_recommendation(
                match_id=match_id,
                game_time=game_time_str,
                dominance=dominance,
                tracking_data=tracking_data,
                elapsed_seconds=elapsed_seconds
            )

    async def _generate_and_broadcast_recommendation(
        self, match_id: str, game_time: str, dominance: float, tracking_data: Dict, elapsed_seconds: int
    ) -> Optional[Dict]:
        try:
            context = {
                "match_id": match_id,
                "game_time": game_time,
                "elapsed_seconds": elapsed_seconds,
                "tracking_data": tracking_data
            }

            if self.mock_mode or not self.analytics_engine:
                rec = self._generate_mock_recommendation(match_id, game_time, dominance, tracking_data)
            else:
                rec = self.analytics_engine.analyze(context)

            if rec and rec.get("coefficient", 0) >= 1.60:
                self.line_cache[match_id] = rec
                logger.info(f"📊 Line generated for {match_id}: {rec.get('line')} @ {rec.get('coefficient')} | Prob: {rec.get('probability')} | Conf: {rec.get('confidence')}")
                # Здесь будет вызов WebSocket-рассылки в Шаге 4
                return rec
            else:
                logger.debug(f"📉 No valid line (coef >= 1.60) for {match_id} at this moment.")
        except Exception as e:
            logger.error(f"💥 Error generating recommendation for {match_id}: {e}")
        return None

    def _generate_mock_recommendation(self, match_id: str, game_time: str, dominance: float, tracking_data: Dict) -> Dict:
        """Fallback-генерация на случай недоступности аналитики"""
        import random
        markets = ["П1", "П2", "ТБ 2.5", "ОЗ Да", "Ф1(-1.5)"]
        weights = [0.35, 0.25, 0.20, 0.15, 0.05]
        selected_market = random.choices(markets, weights=weights, k=1)[0]
        base_coef = random.uniform(1.60, 2.40)
        confidence = "high" if base_coef < 1.90 else "medium"
        return {
            "match_id": match_id,
            "line": selected_market,
            "coefficient": round(base_coef, 2),
            "probability": round(random.uniform(0.55, 0.78), 2),
            "confidence": confidence,
            "game_time": game_time,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }

    def update_official_protocol(self, match_id: str, protocol: Dict) -> None:
        if match_id in self.active_matches:
            self.active_matches[match_id]["protocol"] = protocol

    async def shutdown(self) -> None:
        logger.info("🔌 Shutting down orchestrator...")
        if hasattr(self, 'channel') and self.channel:
            self.channel.close()
        self.active_matches.clear()
        self.line_cache.clear()
        logger.info("✅ Orchestrator stopped.")
