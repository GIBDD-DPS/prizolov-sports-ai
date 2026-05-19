# ============================================
# Prizolov Sports AI - Admin Dashboard & WebSocket Server
# Version: 1.02 (+0.01: Auto Match Context Injection & Live Metadata Broadcasting)
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

# === АВТО-ОПРЕДЕЛЕНИЕ МЕТАДАННЫХ МАТЧА ===
# В продакшене этот словарь должен заполняться из внешней спортивной API (API-Football, SportRadar)
# Для демо — заглушка, которая автоматически подставляется по match_id
MATCH_METADATA_DB = {
    "prod_match_001": {
        "league": "РПЛ",
        "home": "Спартак",
        "away": "Зенит",
        "kickoff": "20:00",
        "country": "RU"
    },
    "live_match_001": {
        "league": "Brasileirão Série A",
        "home": "Vasco da Gama",
        "away": "Corinthians",
        "kickoff": "22:30",
        "country": "BR"
    },
    "default": {
        "league": "Международный турнир",
        "home": "Команда А",
        "away": "Команда Б",
        "kickoff": "--:--",
        "country": "INT"
    }
}

def get_match_metadata(match_id: str) -> Dict[str, str]:
    """Автоматически возвращает метаданные матча по его ID."""
    return MATCH_METADATA_DB.get(match_id, MATCH_METADATA_DB["default"])

class DashboardManager:
    """Менеджер WebSocket-соединений с авто-инжекцией контекста матча."""
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.clients: Set[Any] = set()
        self._last_broadcast_state = None
        self._broadcast_task = None

    async def register(self, websocket, match_id: Optional[str] = None):
        self.clients.add(websocket)
        logger.info(f"🔗 New dashboard client connected. Total active: {len(self.clients)}")
        try:
            # При подключении сразу отправляем полный контекст
            await websocket.send(json.dumps(self._get_current_state(match_id)))
        except (ConnectionClosedError, ConnectionClosedOK):
            await self.unregister(websocket)

    async def unregister(self, websocket):
        self.clients.discard(websocket)
        logger.info(f"🔌 Dashboard client disconnected. Total active: {len(self.clients)}")

    def _get_current_state(self, match_id: Optional[str] = None) -> Dict[str, Any]:
        """Формирует полное состояние дашборда с авто-контекстом матча."""
        # Авто-определение match_id из активных матчей оркестратора
        active_id = match_id or (list(self.orchestrator.active_matches.keys())[0] if self.orchestrator.active_matches else "default")
        
        # Инжекция метаданных матча
        match_info = get_match_metadata(active_id)
        
        # Добавляем live-время, если матч активен
        if active_id in self.orchestrator.active_matches:
            match_data = self.orchestrator.active_matches[active_id]
            start_time = match_data.get("start_time")
            if start_time:
                try:
                    elapsed = int((datetime.utcnow() - datetime.fromisoformat(start_time)).total_seconds())
                    match_info["elapsed_seconds"] = elapsed
                    match_info["game_time"] = f"{elapsed // 60:02d}:{elapsed % 60:02d}"
                except:
                    pass
        
        return {
            "status": "live",
            "match_id": active_id,
            "match_info": match_info,  # <<< НОВОЕ: авто-контекст матча
            "recommendations": list(self.orchestrator.line_cache.values()),
            "active_matches": len(self.orchestrator.active_matches),
            "system_health": "ok",
            "timestamp": datetime.utcnow().isoformat()
        }

    async def broadcast_loop(self, interval: float = 2.0):
        """Периодически отправляет обновления с авто-контекстом всем клиентам."""
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
                        logger.debug("📡 Broadcasted updated state with match context.")
            except Exception as e:
                logger.error(f"💥 Dashboard broadcast loop failed: {e}")
                await asyncio.sleep(1)

    async def handler(self, websocket, path: str = None):
        """Обработчик WebSocket: извлекает match_id из query-параметров или использует дефолт."""
        # Парсинг match_id из URL: ws://.../dashboard?match_id=prod_match_001
        match_id = None
        if path and "?" in path:
            try:
                query = path.split("?")[1]
                params = dict(p.split("=") for p in query.split("&") if "=" in p)
                match_id = params.get("match_id")
            except:
                pass
        
        await self.register(websocket, match_id)
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    action = data.get("action", "").lower()
                    if action == "ping":
                        await websocket.send(json.dumps({"status": "pong", "timestamp": datetime.utcnow().isoformat()}))
                    elif action == "get_state":
                        await websocket.send(json.dumps(self._get_current_state(data.get("match_id"))))
                    elif action == "switch_match":
                        # Позволяет фронтенду запрашивать контекст другого матча
                        new_match_id = data.get("match_id")
                        if new_match_id:
                            await websocket.send(json.dumps(self._get_current_state(new_match_id)))
                    elif action == "set_filter":
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
    if not HAS_WEBSOCKETS:
        raise RuntimeError("WebSocket server cannot start: 'websockets' package is missing.")

    manager = DashboardManager(orchestrator)
    manager._broadcast_task = asyncio.create_task(manager.broadcast_loop(interval=2.0))

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
        logger.info(f"📊 Connect frontend to: ws://<domain>:{port}/dashboard?match_id=YOUR_MATCH_ID")
        return server
    except OSError as e:
        if "Address already in use" in str(e):
            logger.warning(f"⚠️ Port {port} is already in use.")
        else:
            logger.critical(f"🚨 Failed to bind Dashboard Server to port {port}: {e}")
        raise
    except Exception as e:
        logger.critical(f"🚨 Critical Dashboard Server startup error: {e}")
        raise
