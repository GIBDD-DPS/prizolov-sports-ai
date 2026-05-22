# test_aiohttp.py — минимальный тест для CMD/Windows
import asyncio
from aiohttp import web

async def handler(request):
    return web.json_response({"ok": True, "msg": "aiohttp works!"})

async def main():
    app = web.Application()
    app.router.add_get('/test', handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Слушаем на 0.0.0.0:8080
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    
    print("✅ SERVER STARTED", flush=True)
    
    # Держим сервер живым
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    print("🚀 Starting...", flush=True)
    asyncio.run(main())
