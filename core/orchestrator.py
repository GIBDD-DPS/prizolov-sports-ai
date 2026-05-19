# ============================================
# Prizolov Sports AI - Core Orchestrator
# Version: 5.00 (+1.00: Throttled Analysis & Strict Cache Structure Sync)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at cloud.amvera.ru
# ============================================

import os
import asyncio
import logging
import time
import datetime
from typing import Dict, Any, Optional, List

logger = logging.getLogger("PrizolovSportsAI.Orchestrator")

try:
    from agent_bridge.prizolov_agent_pb2_grpc import PrizolovAgentStub
    from agent_bridge.prizolov_agent_pb2 import LineRequest
    import grpc
    HAS_GRPC = True
except ImportError:
    HAS_GRPC = False

try:
    from modules.football import FootballAnalyticsModule
    HAS_FOOTBALL = True
except ImportError:
    HAS_FOOTBALL = False

class PrizolovSportsOrchestrator:
    def __init__(self, target_agent_host: str = "localhost:50051", mock_mode: bool = False, discovery_engine=None):
        self.target_agent_host = target_agent_host
        self.mock_mode = mock_mode or not HAS_GRPC
        self.agent_client = None
        self.discovery_engine = discovery_engine
        self.line_cache: Dict[str, Dict[str, Any]] = {}
        self.last_analysis_time: Dict[str, float] = {}
        self.analyzers = {}

        if HAS_FOOTBALL: self.analyzers["football"] = FootballAnalyticsModule()
        # self.analyzers["hockey"] = HockeyAnalyticsModule()  # Добавить при наличии

        if not self.mock_mode:
            try:
                self.channel = grpc.insecure_channel(target_agent_host)
                self.agent_client = PrizolovAgentStub(self.channel)
            except Exception as e:
                logger.error(f"❌ gRPC fail: {e}")
                self.mock_mode = True

        logger.info(f"🎭 Mock mode: {self.mock_mode} | Analyzers loaded: {list(self.analyzers.keys())}")

    async def run_continuous_scan(self, keep_running_ref=None):
        logger.info("🔁 Запущен цикл автономного сканирования (интервал 60с)")
        while keep_running_ref is None or keep_running_ref():
            try:
                if not self.discovery_engine:
                    await asyncio.sleep(60); continue
                
                events = self.discovery_engine.get_events_for_analysis(hours_ahead=12, min_interest=0.6, limit=15)
                for event in events:
                    await self._analyze_and_cache(event)
                self._prune_stale_matches()
            except Exception as e:
                logger.error(f"💥 Scan cycle error: {e}")
            await asyncio.sleep(60)

    async def _analyze_and_cache(self, event: Dict[str, Any]):
        mid = event["match_id"]
        now = time.time()
        
        # Троттлинг: не анализировать матч чаще чем раз в 45 секунд
        if mid in self.last_analysis_time and (now - self.last_analysis_time[mid]) < 45:
            return
        self.last_analysis_time[mid] = now

        sport = event.get("sport", "unknown")
        analyzer = self.analyzers.get(sport)
        
        context = {
            "match_id": mid, "sport": sport, "league": event["league"],
            "home": event["home_team"], "away": event["away_team"],
            "start_time": event["start_time"], "status": event["status"],
            "tracking_data": {"recent_dominance_ratio": 0.55, "live_xg_a": 0.6, "live_xg_b": 0.4}
        }

        try:
            rec = analyzer.analyze(context) if analyzer and not self.mock_mode else self._mock_analyze(context)
            
            if rec and rec.get("coefficient", 0) >= 1.60:
                self.line_cache[mid] = {
                    "match_context": {
                        "league": event["league"], "home": event["home_team"], 
                        "away": event["away_team"], "sport": sport, "status": event["status"]
                    },
                    "recommendation": rec
                }
                logger.info(f"📊 [{sport.upper()}] {event['home_team']} vs {event['away_team']} | {rec['line']} @ {rec['coefficient']}")
        except Exception as e:
            logger.error(f"💥 Анализ {mid} упал: {e}")

    def _mock_analyze(self, ctx: Dict) -> Dict:
        import random
        markets = ["П1", "П2", "ТБ 2.5", "ОЗ Да", "Ф1(-1.5)", "ИТБ1(1.5)"]
        coef = round(random.uniform(1.60, 2.45), 2)
        prob = round(random.uniform(0.55, 0.78), 2)
        return {
            "match_id": ctx["match_id"], "line": random.choice(markets),
            "coefficient": coef, "probability": prob,
            "confidence": "high" if coef < 1.90 else "medium",
            "timestamp": datetime.datetime.utcnow().isoformat()
        }

    def _prune_stale_matches(self):
        if not self.discovery_engine: return
        active_ids = {e["match_id"] for e in self.discovery_engine.get_all_events()}
        stale = [m for m in self.line_cache if m not in active_ids]
        for m in stale: del self.line_cache[m]
        if stale: logger.info(f"🧹 Удалено {len(stale)} завершённых матчей")

    async def shutdown(self):
        logger.info("🔌 Shutdown orchestrator...")
        if hasattr(self, 'channel') and self.channel: self.channel.close()
        if self.discovery_engine: self.discovery_engine.stop()
        self.line_cache.clear()
        logger.info("✅ Stopped.")
