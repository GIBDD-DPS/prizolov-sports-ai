# core/admin_dashboard.py
# Version: 1.00 (Minimal Export for Amvera - Cannot Fail)
# Author: Dm.Andreyanov | Prizolov Market / Prizolov Lab

import asyncio
import logging
import os
import sys
from aiohttp import web
from datetime import datetime

logger = logging.getLogger("PrizolovSportsAI.Dashboard")

# === CORS: заголовки на ЛЮБОЙ ответ ===
def _cors(resp):
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    resp.headers['Cache-Control'] = 'no-store'
    return resp

# === Обработчик: один ответ для всех маршрутов ===
async def _handle(request):
    data = {
        "status": "ok",
        "service": "Prizolov Sports AI",
        "timestamp": datetime.utcnow().isoformat(),
        "port": os.environ.get("PORT", "8080"),
        "message": "✅ Server running. If you see this, connection works!"
    }
    return _cors(web.json_response(data))

async def _options(request):
    return _cors(web.Response(status=204))

# === ТОЧКА ВХОДА: экспортируется в main.py ===
# Сигнатура должна точно совпадать с вызовом в main.py:
#   await start_api_server(orchestrator, port=port)
async def start_api_server(orchestrator=None, port: int = 8080):
    """
    Минимальный сервер для Amvera.
    - Читает PORT из ENV или использует аргумент
    - Слушает на 0.0.0.0 для Docker
    - Логирует каждый шаг для отладки
    """
    try:
        target_port = int(os.environ.get("PORT", port or 8080))
        logger.info(f"🔧 Starting server on port {target_port}...")
        print(f"🔧 Starting server on port {target_port}...", flush=True)
        
        app = web.Application()
        app.router.add_get('/', _handle)
        app.router.add_get('/api/state', _handle)
        app.router.add_get('/health', _handle)
        app.router.add_options('/{tail:.*}', _options)
        
        runner = web.AppRunner(app)
        await runner.setup()
        logger.info("✅ AppRunner setup complete")
        
        site = web.TCPSite(runner, '0.0.0.0', target_port)
        await site.start()
        logger.info(f"✅ TCPSite started on 0.0.0.0:{target_port}")
        
        # ФИНАЛЬНОЕ логирование, которое ДОЛЖНО появиться в Amvera
        success_msg = f"🚀 DASHBOARD SERVER STARTED on 0.0.0.0:{target_port} (ENV PORT={os.environ.get('PORT', 'not set')})"
        logger.info(success_msg)
        print(f"✅ SERVER READY - Port {target_port}", flush=True)
        sys.stdout.flush()
        
        # Держим сервер живым
        while True:
            await asyncio.sleep(3600)
            
    except Exception as e:
        # Логируем ВСЕ ошибки, чтобы увидеть причину падения
        error_msg = f"💥 FAILED TO START SERVER: {type(e).__name__}: {e}"
        logger.critical(error_msg)
        print(error_msg, flush=True)
        sys.stdout.flush()
        raise  # Переподнимаем, чтобы main.py увидел ошибку
