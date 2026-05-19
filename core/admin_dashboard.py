# ============================================
# Prizolov Sports AI - Admin Dashboard & WebSocket Server
# Version: 1.04 (+0.01: Always-Valid Payload & Graceful Warming State)
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
    HAS_WS = True
except ImportError: HAS_WS = False

logger = logging.getLogger("PrizolovSportsAI.Dashboard")

class DashboardManager:
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.clients: Set[Any] = set()
        self._last = None
        self._task = None

    async def register(self, ws):
        self.clients.add(ws)
        try: await ws.send(json.dumps(self._get_state(), ensure_ascii=False))
        except: await self.unregister(ws)

    async def unregister(self, ws): self.clients.discard(ws)

    def _get_state(self) -> Dict[str, Any]:
        cache = self.orchestrator.line_cache
        flat = []
        primary = {}
        
        if cache:
            mid = next(iter(cache))
            ctx = cache[mid].get("match_context", {})
            primary = {"league": ctx.get("league","—"), "home": ctx.get("home","—"), "away": ctx.get("away","—"), "status": ctx.get("status","LIVE")}
            
            for m, d in cache.items():
                c = d.get("match_context", {})
                r = d.get("recommendation", {})
                if r.get("coefficient",0) >= 1.60:
                    flat.append({**r, "league":c.get("league","—"), "home":c.get("home","—"), "away":c.get("away","—"), "sport":c.get("sport","—")})
        
        # Сортировка и лимит
        flat.sort(key=lambda x: (1 if x.get("confidence")=="high" else 0, x.get("probability",0)), reverse=True)
        
        return {
            "status": "live" if primary else "warming",
            "match_info": primary or {"league":"Загрузка...","home":"—","away":"—","status":"LIVE"},
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
                    await asyncio.gather(*[ws.send(payload) for ws in self.clients], return_exceptions=True)
                    self._last = state
                    logger.debug(f"📡 Broadcasted {len(state['recommendations'])} recs.")
            except Exception as e: logger.error(f"💥 Broadcast err: {e}"); await asyncio.sleep(1)

    async def handler(self, ws, path=None):
        await self.register(ws)
        try:
            async for msg in ws:
                try:
                    d = json.loads(msg)
                    if d.get("action")=="ping": await ws.send(json.dumps({"status":"pong"}))
                    elif d.get("action")=="get_state": await ws.send(json.dumps(self._get_state(), ensure_ascii=False))
                except: pass
        except: pass
        finally: await self.unregister(ws)

async def start_dashboard_server(orchestrator, port: int = 8080):
    if not HAS_WS: raise RuntimeError("websockets missing")
    mgr = DashboardManager(orchestrator)
    mgr._task = asyncio.create_task(mgr.broadcast_loop())
    try:
        srv = await websockets.serve(mgr.handler, "0.0.0.0", port, ping_interval=30, ping_timeout=10)
        logger.info(f"🌐 Dashboard WS started on :{port}")
        return srv
    except Exception as e: logger.critical(f"🚨 WS startup fail: {e}"); raise
