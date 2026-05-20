# ============================================
# Prizolov Sports AI - Admin Dashboard & WebSocket Server
# Version: 1.08 (+0.01: Proxy-Resistant Handshake & Compression Disabled)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at cloud.amvera.ru
# ============================================

import asyncio
import json
import logging
from typing import Set, Dict, Any
from datetime import datetime

try:
    import websockets
    from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK
    HAS_WS = True
except ImportError: 
    HAS_WS = False
    logging.warning("⚠️ websockets missing")

logger = logging.getLogger("PrizolovSportsAI.Dashboard")

# Явное разрешение всех соединений, игнорирование Origin/CORS
async def accept_all_connections(path, request_headers):
    return None  # websockets продолжает handshake

class DashboardManager:
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.clients: Set[Any] = set()
        self._last = None
        self._task = None

    async def register(self, websocket):
        self.clients.add(websocket)
        logger.info(f"🔗 WS Client accepted. Total active: {len(self.clients)}")
        try:
            await websocket.send(json.dumps(self._get_state(), ensure_ascii=False))
        except Exception as e:
            logger.warning(f"⚠️ Failed initial send: {e}")

    async def unregister(self, websocket):
        self.clients.discard(websocket)
        logger.info(f"🔌 WS Client dropped. Total active: {len(self.clients)}")

    def _get_state(self) -> Dict[str, Any]:
        cache = self.orchestrator.line_cache
        flat = []
        primary = {}
        if cache:
            mid = next(iter(cache))
            ctx = cache[mid].get("match_context", {})
            primary = {"league": ctx.get("league","—"), "home": ctx.get("home","—"), "away": ctx.get("away","—"), "status": "LIVE"}
            for m, d in cache.items():
                c = d.get("match_context", {})
                r = d.get("recommendation", {})
                if r.get("coefficient",0) >= 1.60:
                    flat.append({**r, "league":c.get("league","—"), "home":c.get("home","—"), "away":c.get("away","—"), "sport":c.get("sport","—")})
        flat.sort(key=lambda x: (1 if x.get("confidence")=="high" else 0, x.get("probability",0)), reverse=True)
        return {
            "status": "live",
            "match_info": primary or {"league":"Анализ рынка...","home":"—","away":"—","status":"LIVE"},
            "recommendations": flat[:12],
            "total_active": len(cache),
            "timestamp": datetime.utcnow().isoformat()
        }

    async def broadcast_loop(self, interval=2.0):
        while True:
            try:
                await asyncio.sleep(interval)
                state = self._get_state()
                if state != self._last and self.clients:
                    payload = json.dumps(state, ensure_ascii=False)
                    tasks = [ws.send(payload) for ws in list(self.clients)]
                    if tasks:
                        await asyncio.gather(*tasks, return_exceptions=True)
                        self._last = state
                        logger.debug(f"📡 Broadcasted {len(state['recommendations'])} recs")
            except Exception as e:
                logger.error(f"💥 Broadcast loop error: {e}")
                await asyncio.sleep(1)

    async def handler(self, websocket):
        await self.register(websocket)
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    action = data.get("action", "").lower()
                    if action == "ping":
                        await websocket.send(json.dumps({"status": "pong"}))
                    elif action == "get_state":
                        await websocket.send(json.dumps(self._get_state(), ensure_ascii=False))
                except Exception as e:
                    logger.warning(f"Invalid WS message: {e}")
        except ConnectionClosedError: pass
        except Exception as e: logger.error(f"WS Handler error: {e}")
        finally:
            await self.unregister(websocket)

async def start_dashboard_server(orchestrator, port: int = 8080):
    if not HAS_WS: raise RuntimeError("websockets package missing")
    mgr = DashboardManager(orchestrator)
    mgr._task = asyncio.create_task(mgr.broadcast_loop())
    try:
        # Максимальная совместимость с обратными прокси (Nginx/Amvera/Cloudflare)
        # - compression=None: отключает permessage-deflate (часто ломает WS на прокси)
        # - process_request: принимает любой Origin
        # - ping_interval=15: держит соединение живым
        srv = await websockets.serve(
            mgr.handler, 
            "0.0.0.0", 
            port,
            process_request=accept_all_connections,
            compression=None,
            ping_interval=15, 
            ping_timeout=10, 
            close_timeout=5,
            max_size=10**7
        )
        logger.info(f"🌐 Dashboard WS started on :{port} (proxy-optimized)")
        return srv
    except Exception as e:
        logger.critical(f"🚨 WS startup fail: {e}")
        raise
