# ============================================
# Prizolov Sports AI - Admin Dashboard & HTTP API Server
# Version: 2.03 (+0.01: Manual CORS Headers & Explicit 0.0.0.0 Binding)
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
        self.app = web.Application()
        self._setup_routes()

    def _setup_routes(self):
        self.app.router.add_get('/', self.handle_root)
        self.app.router.add_get('/api/state', self.handle_state)
        self.app.router.add_get('/api/health', self.handle_health)
        self.app.router.add_options('/{tail:.*}', self.handle_options)

    def _add_cors_headers(self, response):
        """Добавляет CORS-заголовки вручную к любому ответу"""
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response.headers['Cache-Control'] = 'no-store'
        return response

    def _get_state(self) -> dict:
        cache = self.orchestrator.line_cache
        flat = []
        primary = {}
        if cache:
            mid = next(iter(cache))
            ctx = cache[mid].get("match_context", {})
            primary = {
                "league": ctx.get("league", "—"),
                "home": ctx.get("home", "—"),
                "away": ctx.get("away", "—"),
                "status": ctx.get("status", "LIVE")
            }
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
        flat.sort(key=lambda x: (1 if x.get("confidence") == "high" else 0, x.get("probability", 0)), reverse=True)
        return {
            "status": "live",
            "match_info": primary or {"league": "Анализ рынка...", "home": "—", "away": "—", "status": "LIVE"},
            "recommendations": flat[:12],
            "total_active": len(cache),
            "timestamp": datetime.utcnow().isoformat()
        }

    async def handle_root(self, request):
        resp = web.json_response({"status": "ok", "service": "Prizolov Sports AI API", "version": "2.03"})
        return self._add_cors_headers(resp)

    async def handle_state(self, request):
        try:
            data = self._get_state()
            resp = web.json_response(data, dumps=lambda x: json.dumps(x, ensure_ascii=False))
            return self._add_cors_headers(resp)
        except Exception as e:
            logger.error(f"💥 Error in /api/state: {e}")
            resp = web.json_response({"status": "error", "detail": str(e)}, status=500)
            return self._add_cors_headers(resp)

    async def handle_health(self, request):
        resp = web.json_response({"status": "ok", "timestamp": datetime.utcnow().isoformat()})
        return self._add_cors_headers(resp)

    async def handle_options(self, request):
        resp = web.Response(status=204)
        return self._add_cors_headers(resp)

    async def start_api_server(self, port: int = 8080):
        runner = web.AppRunner(self.app)
        await runner.setup()
        # Явно указываем 0.0.0.0 для работы внутри Docker/Amvera
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        # Логирование ПОСЛЕ успешного старта
        logger.info(f"🌐 HTTP API server STARTED on 0.0.0.0:{port} (CORS enabled manually)")

async def start_api_server(orchestrator, port: int = 8080):
    api = DashboardAPI(orchestrator)
    await api.start_api_server(port)
