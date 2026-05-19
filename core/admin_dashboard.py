# ============================================
# Prizolov Sports AI - Admin Dashboard & WebSocket Server
# Version: 1.03 (+1.01: Dynamic Cache Flattening & Live Multi-Match Broadcast)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at cloud.amvera.ru
# ============================================

import asyncio
import json
import logging
from typing import Set, Dict, Any, Optional
from datetime import datetime

try:
    import websockets
    from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False
    logging.warning("⚠️ websockets package not found. Install via: pip install websockets>=10.0")

logger = logging.getLogger("PrizolovSportsAI.Dashboard")

class DashboardManager:
    """Менеджер WebSocket-соединений с динамической отдачей мульти-спортивного кэша."""
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.clients: Set[Any] = set()
        self._last_broadcast_state = None
        self._broadcast_task = None

    async def register(self, websocket, match_id: Optional[str] = None):
        self.clients.add(websocket)
        logger.info(f"🔗 New dashboard client connected. Total active: {len(self.clients)}")
        try:
            await websocket.send(json.dumps(self._get_current_state(match_id), ensure_ascii=False))
        except (ConnectionClosedError, ConnectionClosedOK):
            await self.unregister(websocket)

    async def unregister(self, websocket):
        self.clients.discard(websocket)
        logger.info(f"🔌 Dashboard client disconnected. Total active: {len(self.clients)}")

    def _get_current_state(self, match_id: Optional[str] = None) -> Dict[str, Any]:
        """Формирует состояние дашборда, динамически извлекая контекст из line_cache оркестратора."""
        cache = self.orchestrator.line_cache
        active_ids = list(cache.keys())

        if not active_ids:
            return {
                "status": "scanning",
                "match_info": {"league": "Поиск событий...", "home": "...", "away": "...", "status": "WAIT"},
                "recommendations": [],
                "total_active": 0,
                "system_health": "ok",
                "timestamp": datetime.utcnow().isoformat()
            }

        # Выбираем основной матч для хедера (запрошенный или первый в кэше)
        primary_id = match_id if match_id in active_ids else active_ids[0]
        primary_data = cache.get(primary_id, {})
        primary_ctx = primary_data.get("match_context", {})

        match_info = {
            "league": primary_ctx.get("league", "—"),
            "home": primary_ctx.get("home", "—"),
            "away": primary_ctx.get("away", "—"),
            "status": primary_ctx.get("status", "LIVE"),
            "sport": primary_ctx.get("sport", "football"),
            "match_id": primary_id
        }

        # Расплющиваем кэш в единый плоский массив рекомендаций для фронтенда
        flat_recs = []
        for mid, data in cache.items():
            ctx = data.get("match_context", {})
            rec = data.get("recommendation", {})
            if rec.get("coefficient", 0) >= 1.60:
                flat_recs.append({
                    "match_id": mid,
                    "league": ctx.get("league", "—"),
                    "home": ctx.get("home", "—"),
                    "away": ctx.get("away", "—"),
                    "sport": ctx.get("sport", "—"),
                    "status": ctx.get("status", "—"),
                    "line": rec.get("line"),
                    "coefficient": rec.get("coefficient"),
                    "probability": rec.get("probability"),
                    "confidence": rec.get("confidence"),
                    "updated_at": rec.get("timestamp")
                })

        # Сортировка: сначала высокий confidence, затем высокая вероятность
        flat_recs.sort(key=lambda x: (
            2 if x.get("confidence") == "high" else (1 if x.get("confidence") == "medium" else 0),
            x.get("probability", 0)
        ), reverse=True)

        return {
            "status": "live",
            "match_info": match_info,
            "recommendations": flat_recs[:15],  # Топ-15 для производительности фронтенда
            "total_active": len(active_ids),
            "system_health": "ok",
            "timestamp": datetime.utcnow().isoformat()
        }

    async def broadcast_loop(self, interval: float = 2.0):
        while True:
            try:
                await asyncio.sleep(interval)
                current_state = self._get_current_state()
                if current_state != self._last_broadcast_state and self.clients:
                    payload = json.dumps(current_state, ensure_ascii=False)
                    send_tasks = [ws.send(payload) for ws in self.clients]
                    if send_tasks:
                        await asyncio.gather(*send_tasks, return_exceptions=True)
                        self._last_broadcast_state = current_state
                        logger.debug(f"📡 Broadcasted {len(current_state['recommendations'])} live recommendations.")
            except Exception as e:
                logger.error(f"💥 Dashboard broadcast loop failed: {e}")
                await asyncio.sleep(1)

    async def handler(self, websocket, path: str = None):
        match_id = None
        if path and "?" in path:
            try:
                query = path.split("?")[1]
                params = dict(p.split("=") for p in query.split("&") if "=" in p)
                match_id = params.get("match_id")
            except: pass
        
        await self.register(websocket, match_id)
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    action = data.get("action", "").lower()
                    if action == "ping":
                        await websocket.send(json.dumps({"status": "pong", "timestamp": datetime.utcnow().isoformat()}))
                    elif action == "get_state":
                        await websocket.send(json.dumps(self._get_current_state(data.get("match_id")), ensure_ascii=False))
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({"error": "Invalid JSON format"}))
        except (ConnectionClosedError, ConnectionClosedOK): pass
        except Exception as e: logger.error(f"💥 WS handler error: {e}")
        finally: await self.unregister(websocket)

async def start_dashboard_server(orchestrator, port: int = 8080):
    if not HAS_WEBSOCKETS: raise RuntimeError("WebSocket server cannot start: 'websockets' package missing.")
    manager = DashboardManager(orchestrator)
    manager._broadcast_task = asyncio.create_task(manager.broadcast_loop(interval=2.0))
    try:
        server = await websockets.serve(manager.handler, "0.0.0.0", port, ping_interval=30, ping_timeout=10, close_timeout=5)
        logger.info(f"🌐 WebSocket Dashboard Server started on ws://0.0.0.0:{port}")
        return server
    except Exception as e:
        logger.critical(f"🚨 Dashboard Server startup error: {e}")
        raise
