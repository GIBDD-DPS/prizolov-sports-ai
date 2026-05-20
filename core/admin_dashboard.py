# ============================================
# Prizolov Sports AI - Admin Dashboard & HTTP API Server
# Version: 2.01 (+0.01: Explicit CORS, OPTIONS Handler & Root Fallback)
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
                    flat.append({**r, "league":c.get("league","—"), "home":c.get("home","—"), "away":c.get("away","—"), "sport":c.get("sport","—")})
        flat.sort(key=lambda x: (1 if x.get("confidence")=="high" else 0, x.get("probability",0)), reverse=True)
        return {
            "status": "live",
            "match_info": primary or {"league":"Анализ рынка...","home":"—","away":"—","status":"LIVE"},
            "recommendations": flat[:12],
            "total_active": len(cache),
            "timestamp": datetime.utcnow().isoformat()
        }

    def _cors_headers(self, resp):
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return resp

    async def handle_state(self, request):
        resp = web.json_response(self._get_state(), dumps=lambda x: json.dumps(x, ensure_ascii=False))
        return self._cors_headers(resp)

    async def handle_health(self, request):
        resp = web.json_response({"status": "ok", "api_version": "2.01"})
        return self._cors_headers(resp)

    async def handle_root(self, request):
        resp = web.json_response({"message": "Prizolov Sports AI API is running", "endpoints": ["/api/state", "/api/health"]})
        return self._cors_headers(resp)

    async def handle_options(self, request):
        resp = web.Response(status=204)
        return self._cors_headers(resp)

    async def start_api_server(self, port: int = 8080):
        app = web.Application()
        app.router.add_get('/api/state', self.handle_state)
        app.router.add_get('/api/health', self.handle_health)
        app.router.add_get('/', self.handle_root)
        app.router.add_route('OPTIONS', '/{tail:.*}', self.handle_options)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        logger.info(f"🌐 HTTP API started on :{port} (CORS enabled, routes: /, /api/state, /api/health)")

async def start_api_server(orchestrator, port: int = 8080):
    api = DashboardAPI(orchestrator)
    await api.start_api_server(port)
