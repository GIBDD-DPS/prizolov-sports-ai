# ============================================
# Prizolov Sports AI - Admin Dashboard & HTTP API Server
# Version: 1.00 (Bulletproof CORS & Hardcoded Port)
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

# === ГЛОБАЛЬНЫЙ CORS MIDDLEWARE: заголовки на ЛЮБОЙ ответ ===
@web.middleware
async def cors_middleware(request, handler):
    try:
        response = await handler(request)
    except web.HTTPException as ex:
        response = ex
    except Exception as e:
        logger.error(f"💥 Middleware error: {e}")
        response = web.json_response({"error": "Internal error"}, status=500)
    
    # Добавляем CORS ко ВСЕМ ответам (200, 404, 500, OPTIONS)
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    return response

# === Обработчик preflight (OPTIONS) запросов ===
async def handle_options(request):
    return web.Response(status=204)

# === Основной обработчик API ===
async def handle_api(request):
    """Единая точка входа: /, /api/state, /health"""
    # Здесь позже будет интеграция с orchestrator.line_cache
    # Пока отдаём тестовый ответ для проверки инфраструктуры
    return web.json_response({
        "status": "ok",
        "service": "Prizolov Sports AI",
        "version": "1.00",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoint": str(request.path),
        "message": "If you see this JSON, the server is running correctly!"
    })

async def start_api_server(orchestrator=None, port: int = None):
    """
    Запускает минимальный HTTP-сервер.
    - Игнорирует ENV, использует жёсткий порт 8080
    - Слушает на 0.0.0.0 для работы в Docker/Amvera
    """
    # Жёсткий порт 8080 (Amvera по умолчанию проксирует на 8080)
    target_port = 8080
    
    app = web.Application(middlewares=[cors_middleware])
    
    # Маршруты: всё идёт в один обработчик для простоты отладки
    app.router.add_get('/', handle_api)
    app.router.add_get('/api/state', handle_api)
    app.router.add_get('/health', handle_api)
    app.router.add_options('/{tail:.*}', handle_options)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    # КРИТИЧЕСКИ ВАЖНО: 0.0.0.0, а не 127.0.0.1
    site = web.TCPSite(runner, '0.0.0.0', target_port)
    await site.start()
    
    # Логирование, которое ДОЛЖНО появиться в Amvera Console
    logger.info(f"🚀 DASHBOARD SERVER STARTED on 0.0.0.0:{target_port}")
    logger.info(f"🌐 Endpoints: /, /api/state, /health")
    logger.info(f"🔐 CORS: Enabled (Access-Control-Allow-Origin: *)")
    print(f"✅ SERVER READY - Port {target_port}", flush=True)
    
    # Держим сервер живым (в реальном приложении здесь был бы event loop)
    while True:
        await asyncio.sleep(3600)
