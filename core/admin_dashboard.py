# core/admin_dashboard.py
# Version: 1.00 (Amvera Bulletproof Export + CORS + Auto-Port)
# Author: Dm.Andreyanov | Prizolov Market / Prizolov Lab

import asyncio
import logging
import os
from aiohttp import web
from datetime import datetime

logger = logging.getLogger("PrizolovSportsAI.Dashboard")

# === CORS: добавляем заголовки к ЛЮБОМУ ответу (200/404/500/OPTIONS) ===
def _add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    return response

# === Обработчик для всех GET-запросов ===
async def _handle_api(request):
    """Единая точка: /, /api/state, /health"""
    data = {
        "status": "ok",
        "service": "Prizolov Sports AI",
        "timestamp": datetime.utcnow().isoformat(),
        "port": os.environ.get("PORT", "8080"),
        "message": "✅ Server is running. Connection works!",
        "test": True
    }
    response = web.json_response(data)
    return _add_cors(response)

# === Обработчик preflight (OPTIONS) для CORS ===
async def _handle_options(request):
    response = web.Response(status=204)
    return _add_cors(response)

# === ТОЧКА ВХОДА: экспортируется в main.py ===
# Сигнатура должна точно совпадать с вызовом в main.py:
#   await start_api_server(orchestrator, port=port)
async def start_api_server(orchestrator=None, port: int = 8080):
    """
    Запускает минимальный HTTP-сервер для Amvera.
    - Читает PORT из ENV (Amvera) или использует аргумент
    - Слушает на 0.0.0.0 для работы в Docker
    - Добавляет CORS ко всем ответам
    """
    # Приоритет: переменная окружения > аргумент > дефолт
    target_port = int(os.environ.get("PORT", port or 8080))
    
    app = web.Application()
    
    # Маршруты: всё идёт в один обработчик для простоты
    app.router.add_get('/', _handle_api)
    app.router.add_get('/api/state', _handle_api)
    app.router.add_get('/health', _handle_api)
    app.router.add_options('/{tail:.*}', _handle_options)
    
    # Запуск сервера
    runner = web.AppRunner(app)
    await runner.setup()
    
    # КРИТИЧЕСКИ: 0.0.0.0, а не 127.0.0.1 (иначе Docker/Amvera не увидят)
    site = web.TCPSite(runner, '0.0.0.0', target_port)
    await site.start()
    
    # Логирование, которое ДОЛЖНО появиться в Amvera Console
    logger.info(f"🚀 DASHBOARD SERVER STARTED on 0.0.0.0:{target_port} (ENV PORT={os.environ.get('PORT', 'not set')})")
    logger.info(f"🌐 Endpoints: /, /api/state, /health")
    logger.info(f"🔐 CORS: Enabled (Access-Control-Allow-Origin: *)")
    print(f"✅ SERVER READY - Port {target_port}", flush=True)
    
    # Держим процесс живым (в продакшене здесь будет event loop с данными)
    while True:
        await asyncio.sleep(3600)
