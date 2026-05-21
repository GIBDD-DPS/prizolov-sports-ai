# ============================================
# Prizolov Sports AI - Core Orchestrator
# Version: 6.00 (+1.00: Throttled Analysis & Strict Cache Structure Sync)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at cloud.amvera.ru
# ============================================

import asyncio
import logging
import time
import datetime
import random
from typing import Dict, Any, Optional, List

logger = logging.getLogger("PrizolovSportsAI.Orchestrator")

try:
    from agent_bridge.prizolov_agent_pb2_grpc import PrizolovAgentStub
    from agent_bridge.prizolov_agent_pb2 import LineRequest
    import grpc
    HAS_GRPC = True
except ImportError: HAS_GRPC = False

try:
    from modules.football import FootballAnalyticsModule
    HAS_FOOTBALL = True
except ImportError: HAS_FOOTBALL = False

class PrizolovSportsOrchestrator:
    def __init__(self, target_agent_host: str = "localhost:50051", mock_mode: bool = False, discovery_engine=None):
        self.target_agent_host = target_agent_host
        self.mock_mode = mock_mode or not HAS_GRPC
        self.agent_client = None
        self.discovery_engine = discovery_engine
        self.line_cache: Dict[str, Dict[str, Any]] = {}
        self.last_analysis: Dict[str, float] = {}
        self.analyzers = {}
        if HAS_FOOTBALL: self.analyzers["football"] = FootballAnalyticsModule()
        
        if not self.mock_mode:
            try:
                self.channel = grpc.insecure_channel(target_agent_host)
                self.agent_client = PrizolovAgentStub(self.channel)
            except Exception as e:
                logger.error(f"❌ gRPC fail: {e}")
                self.mock_mode = True
        logger.info(f"🚀 Orchestrator init. Mock: {self.mock_mode} | Analyzers: {list(self.analyzers.keys())}")

    async def run_initial_analysis(self):
        """Мгновенный анализ пула событий при старте."""
        logger.info("🔥 Running immediate initial analysis...")
        if not self.discovery_engine: return
        events = self.discovery_engine.get_events_for_analysis(hours_ahead=12, min_interest=0.5, limit=10)
        for ev in events: await self._analyze(ev, force=True)
        logger.info(f"✅ Initial analysis complete. Cache size: {len(self.line_cache)}")

    async def run_continuous_scan(self):
        if not self.discovery_engine: return
        events = self.discovery_engine.get_events_for_analysis(hours_ahead=12, min_interest=0.6, limit=10)
        for ev in events: await self._analyze(ev)

    async def _analyze(self, event: Dict[str, Any], force: bool = False):
        mid = event["match_id"]
        now = time.time()
        if not force and mid in self.last_analysis and (now - self.last_analysis[mid]) < 40: return
        self.last_analysis[mid] = now

        sport = event.get("sport", "football")
        analyzer = self.analyzers.get(sport)
        context = {
            "match_id": mid, "sport": sport, "league": event["league"],
            "home": event["home_team"], "away": event["away_team"],
            "status": event["status"], "tracking_data": {"recent_dominance_ratio": 0.55, "live_xg_a": 0.6, "live_xg_b": 0.4}
        }

        try:
            rec = analyzer.analyze(context) if (analyzer and not self.mock_mode) else self._mock_rec(context)
            if rec and rec.get("coefficient", 0) >= 1.60:
                self.line_cache[mid] = {"match_context": context, "recommendation": rec}
                logger.info(f"📊 [{sport.upper()}] {context['home']} vs {context['away']} | {rec['line']} @ {rec['coefficient']}")
        except Exception as e:
            logger.error(f"💥 Analysis fail {mid}: {e}")

    def _mock_rec(self, ctx: Dict) -> Dict:
        m = ["П1", "П2", "ТБ 2.5", "ОЗ Да", "Ф1(-1.5)"]
        c = round(random.uniform(1.60, 2.40), 2)
        p = round(random.uniform(0.55, 0.78), 2)
        return {"match_id": ctx["match_id"], "line": random.choice(m), "coefficient": c, "probability": p, "confidence": "high" if c<1.9 else "medium", "timestamp": datetime.datetime.utcnow().isoformat()}

    def _prune(self):
        if not self.discovery_engine: return
        active = {e["match_id"] for e in self.discovery_engine.get_all_events()}
        stale = [m for m in self.line_cache if m not in active]
        for m in stale: del self.line_cache[m]

    async def shutdown(self):
        logger.info("🔌 Shutdown...")
        if hasattr(self, 'channel') and self.channel: self.channel.close()
        if self.discovery_engine: self.discovery_engine.stop()
        self.line_cache.clear()
