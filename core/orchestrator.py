# ============================================
# Prizolov Sports AI - Core Orchestrator
# Version: 4.06 (+1.01: Multi-Sport Dynamic Discovery Routing & Live Pool Management)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at cloud.amvera.ru
# ============================================

import os
import asyncio
import logging
import datetime
from typing import Dict, Any, Optional, List

logger = logging.getLogger("PrizolovSportsAI.Orchestrator")

# Безопасный импорт gRPC
try:
    from agent_bridge.prizolov_agent_pb2_grpc import PrizolovAgentStub
    from agent_bridge.prizolov_agent_pb2 import LineRequest
    import grpc
    HAS_GRPC = True
except ImportError:
    HAS_GRPC = False
    logger.warning("⚠️ gRPC modules not found. Mock mode will be forced.")

# Безопасный импорт аналитических модулей
try:
    from modules.football import FootballAnalyticsModule
    HAS_FOOTBALL_ANALYTICS = True
except ImportError:
    HAS_FOOTBALL_ANALYTICS = False

class PrizolovSportsOrchestrator:
    def __init__(self, target_agent_host: str = "localhost:50051", mock_mode: bool = False, discovery_engine=None):
        self.target_agent_host = target_agent_host
        self.mock_mode = mock_mode or not HAS_GRPC
        self.agent_client = None
        self.line_cache: Dict[str, Dict[str, Any]] = {}
        self.discovery_engine = discovery_engine
        self.analyzers: Dict[str, Any] = {}

        # Инициализация роутера анализаторов по видам спорта
        if HAS_FOOTBALL_ANALYTICS:
            self.analyzers["football"] = FootballAnalyticsModule()
        # Здесь можно добавить self.analyzers["hockey"] = HockeyAnalyticsModule() и т.д.
        
        if not self.mock_mode:
            try:
                self.channel = grpc.insecure_channel(target_agent_host)
                self.agent_client = PrizolovAgentStub(self.channel)
                logger.info(f"✅ gRPC channel established to {target_agent_host}")
            except Exception as e:
                logger.error(f"❌ Failed to connect to Agent OS: {e}")
                self.mock_mode = True

        if self.mock_mode or not self.analyzers:
            logger.info("🎭 Orchestrator running in MOCK/SAFE MODE. Using synthetic analysis pipeline.")

    async def run_continuous_scan(self, keep_running_ref=None):
        """Основной цикл: сканирует события, анализирует, обновляет кэш для дашборда."""
        logger.info("🔁 Запущен непрерывный цикл анализа событий...")
        scan_interval = 60  # секунд
        
        while keep_running_ref is None or keep_running_ref():
            try:
                if not self.discovery_engine:
                    await asyncio.sleep(scan_interval)
                    continue

                # 1. Получаем отфильтрованные события
                events = self.discovery_engine.get_events_for_analysis(
                    hours_ahead=12, min_interest=0.6, limit=15
                )
                
                if not events:
                    logger.debug("⏳ Нет интересных событий для анализа. Ожидание...")
                    await asyncio.sleep(scan_interval)
                    continue

                # 2. Анализируем каждое событие
                for event in events:
                    await self.analyze_event(event)
                
                # 3. Очистка кэша от завершённых матчей
                self._prune_finished_matches(events)
                
            except Exception as e:
                logger.error(f"💥 Ошибка в цикле сканирования: {e}")
            
            await asyncio.sleep(scan_interval)

    async def analyze_event(self, event: Dict[str, Any]):
        """Анализ одного события через роутер анализаторов или mock-режим."""
        match_id = event["match_id"]
        sport = event.get("sport", "unknown")
        context = {
            "match_id": match_id,
            "sport": sport,
            "league": event["league"],
            "home": event["home_team"],
            "away": event["away_team"],
            "start_time": event["start_time"],
            "status": event["status"],
            "tracking_data": {
                "recent_dominance_ratio": 0.55,
                "live_xg_a": 0.6, "live_xg_b": 0.4,
                "danger_attacks_a": 3, "danger_attacks_b": 2
            }
        }

        try:
            if self.mock_mode or sport not in self.analyzers:
                rec = self._generate_mock_recommendation(context)
            else:
                rec = self.analyzers[sport].analyze(context)
            
            if rec and rec.get("coefficient", 0) >= 1.60:
                # Сохраняем в кэш с полным контекстом для фронтенда
                self.line_cache[match_id] = {
                    "match_context": {
                        "league": event["league"],
                        "home": event["home_team"],
                        "away": event["away_team"],
                        "start_time": event["start_time"],
                        "status": event["status"]
                    },
                    "recommendation": rec,
                    "updated_at": datetime.datetime.utcnow().isoformat()
                }
                logger.info(f"📊 [{sport.upper()}] {event['home']} vs {event['away']} | {rec['line']} @ {rec['coefficient']}")
        except Exception as e:
            logger.error(f"💥 Анализ {match_id} упал: {e}")

    def _prune_finished_matches(self, active_events: List[Dict]):
        active_ids = {e["match_id"] for e in active_events}
        to_remove = [mid for mid in self.line_cache if mid not in active_ids]
        for mid in to_remove:
            del self.line_cache[mid]
        if to_remove:
            logger.info(f"🧹 Удалено {len(to_remove)} завершённых матчей из кэша")

    def _generate_mock_recommendation(self, context: Dict) -> Dict:
        import random
        markets = ["П1", "П2", "ТБ 2.5", "ОЗ Да", "Ф1(-1.5)", "ИТБ1(72.5)"]
        market = random.choice(markets)
        coef = round(random.uniform(1.60, 2.40), 2)
        prob = round(random.uniform(0.55, 0.78), 2)
        conf = "high" if coef < 1.90 else "medium"
        return {
            "match_id": context["match_id"],
            "line": market,
            "coefficient": coef,
            "probability": prob,
            "confidence": conf,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }

    async def shutdown(self) -> None:
        logger.info("🔌 Shutting down orchestrator...")
        if hasattr(self, 'channel') and self.channel:
            self.channel.close()
        if self.discovery_engine:
            self.discovery_engine.stop()
        self.line_cache.clear()
        logger.info("✅ Orchestrator stopped.")
