#!/usr/bin/env python3
# ============================================
# Prizolov Sports AI - Admin Dashboard / API Layer
# Version: 1.02 (PRODUCTION OPTIMIZED FOR GATHER/AMVERA)
# Author: Dm.Andreyanov / Refactored
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at cloud.amvera.ru
# ============================================

import asyncio
import logging
import os
import sys
from aiohttp import web
from datetime import datetime

logger = logging.getLogger("PrizolovSportsAI.Dashboard")


# ============================================================
# CORS WRAPPER
# ============================================================

def _cors(resp):
    """Добавляет CORS‑заголовки к любому ответу."""
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    resp.headers['Cache-Control'] = 'no-store'
    return resp


async def _options(request):
    """Ответ на preflight‑запросы."""
    return _cors(web.Response(status=204))


# ============================================================
# BASIC STATUS HANDLER
# ============================================================

async def _handle_status(request):
    """Базовый статус‑эндпоинт (используется Amvera для Healthcheck)."""
    data = {
        "status": "ok",
        "service": "Prizolov Sports AI",
        "timestamp": datetime.utcnow().isoformat(),
        "port": os.environ.get("PORT", "8080"),
        "message": "✅ Server running. Connection OK."
    }
    return _cors(web.json_response(data))


# ============================================================
# API: CACHE (для WordPress/Elementor)
# ============================================================

async def _handle_cache(request):
    orch = request.app.get("orchestrator")
    if not orch:
        return _cors(web.json_response({"error": "orchestrator_not_available"}, status=500))

    try:
        # Безопасное получение кэша линий
        cache = getattr(orch, 'line_cache', {})
        return _cors(web.json_response({
            "status": "ok",
            "count": len(cache),
            "data": cache,
            "timestamp": datetime.utcnow().isoformat()
        }))
    except Exception as e:
        logger.error(f"💥 CACHE ERROR: {e}")
        return _cors(web.json_response({"error": "cache_read_fail"}, status=500))


# ============================================================
# API: EVENTS (для WordPress/Elementor)
# ============================================================

async def _handle_events(request):
    orch = request.app.get("orchestrator")
    if not orch or not getattr(orch, 'discovery_engine', None):
        return _cors(web.json_response({"error": "discovery_not_available"}, status=500))

    try:
        events = orch.discovery_engine.get_all_events()
        return _cors(web.json_response({
            "status": "ok",
            "count": len(events),
            "events": events,
            "timestamp": datetime.utcnow().isoformat()
        }))
    except Exception as e:
        logger.error(f"💥 EVENTS ERROR: {e}")
        return _cors(web.json_response({"error": "events_read_fail"}, status=500))


# ============================================================
# START SERVER (экспортируется в main.py)
# ============================================================

async def start_api_server(orchestrator=None, port: int = 8080):
    """
    Минимальный и неблокирующий сервер для Amvera.
    - Читает PORT из ENV или использует аргумент.
    - Слушает на 0.0.0.0 для Docker.
    - Не блокирует выполнение фонового цикла ИИ-оркестратора.
    """
    try:
        target_port = int(os.environ.get("PORT", port or 8080))
        logger.info(f"🔧 Starting server on port {target_port}...")
        print(f"🔧 Starting server on port {target_port}...", flush=True)

        app = web.Application()
        app["orchestrator"] = orchestrator

        # Базовые маршруты и Healthcheck
        app.router.add_get('/', _handle_status)
        app.router.add_get('/health', _handle_status)
        app.router.add_get('/api/state', _handle_status)

        # API‑маршруты для интеграции с сайтом (WP / Elementor)
        app.router.add_get('/api/cache', _handle_cache)
        app.router.add_get('/api/events', _handle_events)

        # CORS preflight
        app.router.add_options('/{tail:.*}', _options)

        # Инициализация раннера aiohttp
        runner = web.AppRunner(app)
        await runner.setup()
        logger.info("✅ AppRunner setup complete")

        # Запуск TCP-сайта
        site = web.TCPSite(runner, '0.0.0.0', target_port)
        await site.start()
        logger.info(f"✅ TCPSite started on 0.0.0.0:{target_port}")

        print(f"✅ SERVER READY - Port {target_port}", flush=True)
        sys.stdout.flush()

        # [УБРАНО СТАРОЕ ОЖИДАНИЕ WHLLE TRUE]
        # Возвращаем управление в main.py, чтобы aiohttp работал параллельно с ИИ-сканированием
        return runner

    except Exception as e:
        error_msg = f"💥 FAILED TO START SERVER: {type(e).__name__}: {e}"
        logger.critical(error_msg)
        print(error_msg, flush=True)
        sys.stdout.flush()
        raise
