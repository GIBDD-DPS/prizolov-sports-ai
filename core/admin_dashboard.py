# ============================================
# Prizolov Sports AI - Admin Dashboard & HTTP API Server
# Version: 2.02 (+0.01: Robust Async Startup & Explicit Port Binding)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at cloud.amvera.ru
# ============================================

import asyncio
import json
import logging
from datetime import datetime

try:
    from aiohttp import web
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False
    logging.critical("❌ aiohttp is missing! Please check requirements.txt")

logger = logging.getLogger("PrizolovSportsAI.Dashboard")

class DashboardAPI:
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self._runner = None

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
                    flat.append({**r, "league":c.get("league","—"), "home":c.get("home","—"), "away":c.get("away","—"), "sport":c.get("sport","—")})
        flat.sort(key=lambda x: (1 if x.get("confidence")=="high" else 0, x.get("probability",0)), reverse=True)
        return {
            "status": "live",
            "match_info": primary or {"league":"Анализ рынка...","home":"—","away":"—","status":"LIVE"},
            "recommendations": flat[:12],
            "total_active": len(cache),
            "timestamp": datetime.utcnow().isoformat()
        }

    def _add_cors(self, response):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response

    async def handle_state(self, request):
        resp = web.json_response(self._get_state(), dumps=lambda x: json.dumps(x, ensure_ascii=False))
        return self._add_cors(resp)

    async def handle_health(self, request):
        resp = web.json_response({"status": "ok", "api_version": "2.02"})
        return self._add_cors(resp)

    async def handle_root(self, request):
        resp = web.json_response({"message": "Prizolov Sports AI API is running", "endpoints": ["/api/state", "/api/health"]})
        return self._add_cors(resp)

    async def handle_options(self, request):
        return self._add_cors(web.Response(status=204))

    async def start_api_server(self, port: int = 8080):
        if not HAS_AIOHTTP: raise RuntimeError("aiohttp package missing")
        try:
            app = web.Application()
            app.router.add_get('/api/state', self.handle_state)
            app.router.add_get('/api/health', self.handle_health)
            app.router.add_get('/', self.handle_root)
            app.router.add_route('OPTIONS', '/{tail:.*}', self.handle_options)
            
            self._runner = web.AppRunner(app)
            await self._runner.setup()
            site = web.TCPSite(self._runner, '0.0.0.0', port)
            await site.start()
            logger.info(f"🌐 HTTP API started on 0.0.0.0:{port} (CORS enabled)")
        except Exception as e:
            logger.critical(f"🚨 Failed to start HTTP API server: {e}")
            raise

async def start_api_server(orchestrator, port: int = 8080):
    api = DashboardAPI(orchestrator)
    await api.start_api_server(port)
