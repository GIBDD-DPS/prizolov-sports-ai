# core/admin_dashboard.py
# Version: 1.00 (Minimal Bulletproof Export for Amvera)
import asyncio
import logging
from aiohttp import web
from datetime import datetime

logger = logging.getLogger("PrizolovSportsAI.Dashboard")

# === CORS: добавляем заголовки ко ВСЕМ ответам ===
def add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Cache-Control'] = 'no-store'
    return response

# === Обработчики ===
async def handle_api(request):
    """Единый ответ для /, /api/state, /health"""
    data = {
        "status": "ok",
        "service": "Prizolov Sports AI",
        "timestamp": datetime.utcnow().isoformat(),
        "message": "Server is running on Amvera",
        "test": True
    }
    response = web.json_response(data)
    return add_cors(response)

async def handle_options(request):
    """Preflight для CORS"""
    response = web.Response(status=204)
    return add_cors(response)

# === ТОЧКА ВХОДА: экспортируется в main.py ===
async def start_api_server(orchestrator=None, port: int = 8080):
    """
    Запускает минимальный HTTP-сервер.
    Сигнатура: совместима с вызовом в main.py
    """
    app = web.Application()
    
    # Маршруты
    app.router.add_get('/', handle_api)
    app.router.add_get('/api/state', handle_api)
    app.router.add_get('/health', handle_api)
    app.router.add_options('/{tail:.*}', handle_options)
    
    # Запуск
    runner = web.AppRunner(app)
    await runner.setup()
    
    # КРИТИЧЕСКИ: 0.0.0.0 для работы в Docker/Amvera
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    # Логирование
    logger.info(f"🚀 SERVER STARTED on 0.0.0.0:{port}")
    print(f"✅ SERVER READY - Port {port}", flush=True)
    
    # Держим сервер живым
    while True:
        await asyncio.sleep(3600)
