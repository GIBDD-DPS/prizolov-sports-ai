# ============================================
# Prizolov Sports AI - Admin Dashboard & HTTP API Server
# Version: 1.00 (Correct Module-Level Export for main.py)
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

# === ГЛОБАЛЬНЫЙ CORS MIDDLEWARE ===
@web.middleware
async def cors_middleware(request, handler):
    try:
        response = await handler(request)
    except web.HTTPException as ex:
        response = ex
    except Exception as e:
        logger.error(f"💥 Middleware error: {e}")
        response = web.json_response({"error": "Internal error"}, status=500)
    
    # CORS для ВСЕХ ответов
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Cache-Control'] = 'no-store'
    return response

# === Обработчик OPTIONS (preflight) ===
async def handle_options(request):
    return web.Response(status=204)

# === Основной обработчик API ===
async def handle_api(request):
    """Единая точка: /, /api/state, /health"""
    # TODO: Интеграция с orchestrator.line_cache
    return web.json_response({
        "status": "ok",
        "service": "Prizolov Sports AI",
        "timestamp": datetime.utcnow().isoformat(),
        "message": "Server is running. Waiting for orchestrator integration."
    })

# === ТОЧКА ВХОДА ДЛЯ ИМПОРТА В main.py ===
async def start_api_server(orchestrator=None, port: int = 8080):
    """
    Запускает HTTP-сервер.
    Сигнатура соответствует вызову в main.py: start_api_server(orch, port=port)
    """
    # Жёсткий порт 8080 для Amvera
    target_port = port if port else 8080
    
    app = web.Application(middlewares=[cors_middleware])
    
    # Маршруты
    app.router.add_get('/', handle_api)
    app.router.add_get('/api/state', handle_api)
    app.router.add_get('/health', handle_api)
    app.router.add_options('/{tail:.*}', handle_options)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    # КРИТИЧЕСКИ: 0.0.0.0 для Docker/Amvera
    site = web.TCPSite(runner, '0.0.0.0', target_port)
    await site.start()
    
    # Логирование для отладки
    logger.info(f"🚀 DASHBOARD SERVER STARTED on 0.0.0.0:{target_port}")
    logger.info(f"🌐 Endpoints: /, /api/state, /health")
    print(f"✅ SERVER READY - Port {target_port}", flush=True)
    
    # Держим сервер живым
    while True:
        await asyncio.sleep(3600)
