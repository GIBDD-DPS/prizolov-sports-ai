# ============================================
# Prizolov Sports AI - Admin Dashboard & HTTP API Server
# Version: 2.00 (+1.00: WebSocket → HTTP Polling Migration for PaaS Compatibility)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at cloud.amvera.ru
# ============================================

import asyncio
import json
import logging
from aiohttp import web
from datetime import datetime

logger = logging.getLogger("PrizolovSportsAI.Dashboard")

class DashboardAPI:
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator

    def _get_state(self) -> dict:
        cache = self.orchestrator.line_cache
        flat = []
        primary = {}
        
        if cache:
            mid = next(iter(cache))
            ctx = cache[mid].get("match_context", {})
            primary = {"league": ctx.get("league","—"), "home": ctx.get("home","—"), "away": ctx.get("away","—"), "status": "LIVE"}
            for m, d in cache.items():
                c = d.get("match_context", {})
                r = d.get("recommendation", {})
                if r.get("coefficient", 0) >= 1.60:
                    flat.append({
                        **r, 
                        "league": c.get("league", "—"), 
                        "home": c.get("home", "—"), 
                        "away": c.get("away", "—"), 
                        "sport": c.get("sport", "—")
                    })
        
        # Сортировка: high confidence → high probability
        flat.sort(key=lambda x: (1 if x.get("confidence") == "high" else 0, x.get("probability", 0)), reverse=True)
        
        return {
            "status": "live",
            "match_info": primary or {"league": "Анализ рынка...", "home": "—", "away": "—", "status": "LIVE"},
            "recommendations": flat[:12],
            "total_active": len(cache),
            "timestamp": datetime.utcnow().isoformat()
        }

    async def handle_state(self, request):
        response = web.json_response(self._get_state(), dumps=lambda x: json.dumps(x, ensure_ascii=False))
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

    async def handle_health(self, request):
        response = web.json_response({"status": "ok", "timestamp": datetime.utcnow().isoformat()})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

    async def start_api_server(self, port: int = 8080):
        app = web.Application()
        app.router.add_get('/api/state', self.handle_state)
        app.router.add_get('/api/health', self.handle_health)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        logger.info(f"🌐 HTTP Polling API started on :{port}/api/state (100% Proxy Compatible)")

# Сохраняем старую сигнатуру для совместимости с main.py
async def start_api_server(orchestrator, port: int = 8080):
    api = DashboardAPI(orchestrator)
    await api.start_api_server(port)
