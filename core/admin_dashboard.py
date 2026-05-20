# ============================================
# Prizolov Sports AI - Minimal HTTP Server (No ENV)
# Version: 1.00 (Hardcoded Port 8080)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

import asyncio
import json
import logging
from aiohttp import web
from datetime import datetime

logger = logging.getLogger("PrizolovSportsAI.MinimalAPI")

# === ГЛОБАЛЬНЫЙ CORS: заголовки на ВСЕ ответы ===
@web.middleware
async def cors_middleware(request, handler):
    try:
        response = await handler(request)
    except web.HTTPException as ex:
        response = ex
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Cache-Control'] = 'no-store'
    return response

async def handle_api(request):
    """Единый обработчик для / и /api/state"""
    return web.json_response({
        "status": "ok",
        "service": "Prizolov Sports AI",
        "timestamp": datetime.utcnow().isoformat(),
        "test": "Server is running on hardcoded port 8080",
        "endpoint": str(request.url)
    })

async def start_server():
    app = web.Application(middlewares=[cors_middleware])
    app.router.add_route('*', '/{tail:.*}', handle_api)
    
    runner = web.AppRunner(app)
    await runner.setup()
    # ЖЁСТКАЯ привязка: 0.0.0.0:8080 (никаких ENV)
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    
    # Критически важное логирование
    logger.info("🚀 SERVER STARTED on 0.0.0.0:8080 (HARDCODED, NO ENV)")
    logger.info("🌐 Test: curl http://localhost:8080/api/state")
    
    # Держим процесс живым
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    asyncio.run(start_server())
