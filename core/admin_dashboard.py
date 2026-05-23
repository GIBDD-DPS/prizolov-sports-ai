# core/admin_dashboard.py
# Version: 1.00 (Amvera-Ready: Correct Export + Auto-Port + CORS)
import asyncio
import logging
import os
from aiohttp import web
from datetime import datetime

logger = logging.getLogger("PrizolovSportsAI.Dashboard")

# === CORS: заголовки на ЛЮБОЙ ответ (включая 500/404) ===
def _cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Cache-Control'] = 'no-store'
    return response

# === Обработчики ===
async def _handle(request):
    """Единый ответ для /, /api/state, /health"""
    data = {
        "status": "ok",
        "service": "Prizolov Sports AI",
        "timestamp": datetime.utcnow().isoformat(),
        "port": os.environ.get("PORT", "8080"),
        "message": "✅ Server running. If you see this JSON, connection works!"
    }
    return _cors(web.json_response(data))

async def _options(request):
    """Preflight для CORS"""
    return _cors(web.Response(status=204))

# === ТОЧКА ВХОДА: экспортируется в main.py ===
# Сигнатура должна точно совпадать с вызовом в main.py:
#   await start_api_server(orchestrator, port=port)
async def start_api_server(orchestrator=None, port: int = 8080):
    """
    Запускает минимальный HTTP-сервер.
    - Читает PORT из ENV (Amvera) или использует аргумент
    - Слушает на 0.0.0.0 для работы в Docker
    """
    # Приоритет: ENV > аргумент > дефолт
    target_port = int(os.environ.get("PORT", port or 8080))
    
    app = web.Application()
    app.router.add_get('/', _handle)
    app.router.add_get('/api/state', _handle)
    app.router.add_get('/health', _handle)
    app.router.add_options('/{tail:.*}', _options)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    # КРИТИЧЕСКИ: 0.0.0.0, а не 127.0.0.1
    site = web.TCPSite(runner, '0.0.0.0', target_port)
    await site.start()
    
    # Логирование для отладки в Amvera Console
    logger.info(f"🚀 SERVER STARTED on 0.0.0.0:{target_port} (ENV PORT={os.environ.get('PORT', 'not set')})")
    print(f"✅ SERVER READY - Port {target_port}", flush=True)
    
    # Держим процесс живым
    while True:
        await asyncio.sleep(3600)
