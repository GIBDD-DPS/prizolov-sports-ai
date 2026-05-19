# ============================================
# Prizolov Sports AI - Admin Dashboard & WebSocket Server
# Version: 1.01 (+1.01: Real-time WebSocket Broadcasting Engine for prizolov.ru/sport/)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at cloud.amvera.ru
# ============================================

import asyncio
import json
import logging
from typing import Set, Dict, Any
from datetime import datetime

# Безопасный импорт websockets (стандарт для async WS в Python)
try:
    import websockets
    from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False
    logging.warning("⚠️ websockets package not found. Install via: pip install websockets>=10.0")

logger = logging.getLogger("PrizolovSportsAI.Dashboard")

class DashboardManager:
    """Менеджер WebSocket-соединений и периодической трансляции данных."""
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.clients: Set[Any] = set()
        self._last_broadcast_state = None
        self._broadcast_task = None

    async def register(self, websocket):
        self.clients.add(websocket)
        logger.info(f"🔗 New dashboard client connected. Total active: {len(self.clients)}")
        try:
            await websocket.send(json.dumps(self._get_current_state()))
        except (ConnectionClosedError, ConnectionClosedOK):
            await self.unregister(websocket)

    async def unregister(self, websocket):
        self.clients.discard(websocket)
        logger.info(f"🔌 Dashboard client disconnected. Total active: {len(self.clients)}")

    def _get_current_state(self) -> Dict[str, Any]:
        """Формирует состояние дашборда на основе кэша оркестратора."""
        return {
            "status": "live",
            "recommendations": list(self.orchestrator.line_cache.values()),
            "active_matches": len(self.orchestrator.active_matches),
            "system_health": "ok",
            "timestamp": datetime.utcnow().isoformat()
        }

    async def broadcast_loop(self, interval: float = 2.0):
        """Периодически отправляет обновления всем подключенным клиентам."""
        while True:
            try:
                await asyncio.sleep(interval)
                current_state = self._get_current_state()
                
                # Отправляем только если данные изменились и есть клиенты
                if current_state != self._last_broadcast_state and self.clients:
                    payload = json.dumps(current_state, ensure_ascii=False)
                    # Асинхронная рассылка с игнорированием ошибок закрытых соединений
                    send_tasks = [
                        ws.send(payload) 
                        for ws in self.clients
                    ]
                    if send_tasks:
                        await asyncio.gather(*send_tasks, return_exceptions=True)
                        self._last_broadcast_state = current_state
                        logger.debug("📡 Broadcasted updated recommendations to all clients.")
            except Exception as e:
                logger.error(f"💥 Dashboard broadcast loop failed: {e}")
                await asyncio.sleep(1)  # Предотвращаем busy-loop при ошибках

    async def handler(self, websocket, path: str = None):
        """Основной обработчик WebSocket-соединений."""
        await self.register(websocket)
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    action = data.get("action", "").lower()
                    if action == "ping":
                        await websocket.send(json.dumps({"status": "pong", "timestamp": datetime.utcnow().isoformat()}))
                    elif action == "get_state":
                        await websocket.send(json.dumps(self._get_current_state()))
                    elif action == "set_filter":
                        # Заготовка для фильтрации на стороне сервера (коэф, спорт, уверенность)
                        logger.info(f"🔍 Client requested filter: {data.get('criteria', {})}")
                        await websocket.send(json.dumps({"status": "filter_acknowledged"}))
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({"error": "Invalid JSON format"}))
        except (ConnectionClosedError, ConnectionClosedOK):
            logger.info("🔌 Client connection closed normally.")
        except Exception as e:
            logger.error(f"💥 Unexpected WS error: {e}")
        finally:
            await self.unregister(websocket)

async def start_dashboard_server(orchestrator, port: int = 8080):
    """
    Точка входа из main.py. Запускает WebSocket-сервер на заданном порту.
    """
    if not HAS_WEBSOCKETS:
        raise RuntimeError("WebSocket server cannot start: 'websockets' package is missing.")

    manager = DashboardManager(orchestrator)
    
    # Запуск фонового цикла рассылки
    manager._broadcast_task = asyncio.create_task(manager.broadcast_loop(interval=2.0))

    # Инициализация сервера (совместимо с websockets >= 10.0)
    try:
        server = await websockets.serve(
            manager.handler,
            "0.0.0.0",
            port,
            ping_interval=30,
            ping_timeout=10,
            close_timeout=5
        )
        logger.info(f"🌐 WebSocket Dashboard Server started on ws://0.0.0.0:{port}")
        logger.info(f"📊 Connect frontend to: ws://<your-domain>:{port}/")
        return server
    except OSError as e:
        if "Address already in use" in str(e):
            logger.warning(f"⚠️ Port {port} is already in use. Dashboard may not be accessible.")
        else:
            logger.critical(f"🚨 Failed to bind Dashboard Server to port {port}: {e}")
        raise
    except Exception as e:
        logger.critical(f"🚨 Critical Dashboard Server startup error: {e}")
        raise
