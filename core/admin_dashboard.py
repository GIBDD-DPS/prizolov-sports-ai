# ============================================
# Prizolov Sports AI - Admin Dashboard & HTTP API Server
# Version: 2.03 (+0.01: CORS Middleware, Root Route Fallback & Cache-Control)
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

# CORS Middleware для aiohttp
@web.middleware
async def cors_and_security_middleware(request, handler):
    # Обработка preflight запросов
    if request.method == "OPTIONS":
        return web.Response(status=200)
    
    response = await handler(request)
    
    # Явные заголовки для обхода CORS и кэширования прокси
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Accept, Authorization'
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, proxy-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

class DashboardAPI:
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.app = web.Application(middlewares=[cors_and_security_middleware])
        
        # Маршруты: явный API и fallback на корень
        self.app.router.add_get('/api/state', self.handle_state)
        self.app.router.add_get('/api/health', self.handle_health)
        self.app.router.add_get('/', self.handle_state)

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

    async def handle_state(self, request):
        try:
            data = self._get_state()
            return web.json_response(data, dumps=lambda x: json.dumps(x, ensure_ascii=False))
        except Exception as e:
            logger.error(f"💥 State handler failed: {e}")
            return web.json_response({"error": "Internal server error", "status": "error"}, status=500)

    async def handle_health(self, request):
        return web.json_response({"status": "ok", "api_version": "2.03", "timestamp": datetime.utcnow().isoformat()})

    async def start_api_server(self, port: int = 8080):
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        logger.info(f"🌐 HTTP API started on 0.0.0.0:{port} (CORS enabled, routes: /, /api/state)")

async def start_api_server(orchestrator, port: int = 8080):
    api = DashboardAPI(orchestrator)
    await api.start_api_server(port)
