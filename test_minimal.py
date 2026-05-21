#!/usr/bin/env python3
# Минимальный тестовый сервер — гарантированно запустится
import asyncio
from aiohttp import web

async def handler(request):
    return web.json_response({
        "status": "ok",
        "message": "MINIMAL SERVER IS RUNNING",
        "path": request.path
    }, headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type"
    })

async def options_handler(request):
    return web.Response(status=204, headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type"
    })

async def start():
    app = web.Application()
    app.router.add_get('/api/state', handler)
    app.router.add_get('/', handler)
    app.router.add_options('/{tail:.*}', options_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    # КРИТИЧЕСКИ: 0.0.0.0 для Docker и 127.0.0.1 для локального теста
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    
    print("✅ MINIMAL SERVER STARTED on 0.0.0.0:8080", flush=True)
    print("🔗 Test: curl http://localhost:8080/api/state", flush=True)
    
    # Держим сервер живым
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    print("🚀 Starting minimal test server...", flush=True)
    asyncio.run(start())
