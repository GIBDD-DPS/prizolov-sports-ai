#!/usr/bin/env python3
# ============================================
# Prizolov Sports AI - Main Execution Engine
# Version: 8.52 (+0.01: Fix EventDiscoveryEngine Instantiation)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at cloud.amvera.ru
# ============================================

import sys
import os
import argparse
import asyncio
import signal
import logging
import pathlib
import random
import datetime
import time

# === ЖЁСТКИЙ БАННЕР ВЕРСИИ ===
print("="*50)
print("🚀 PRIZOLOV SPORTS AI v8.52 STARTED")
print("📅 UTC:", datetime.datetime.utcnow().isoformat())
print("🔧 Mock Mode: ACTIVE | Discovery: ENABLED")
print("="*50)
sys.stdout.flush()

# Инжекция типов
import builtins, typing
for a, v in [('Path', pathlib.Path), ('Tuple', typing.Tuple), ('List', typing.List), ('Dict', typing.Dict), ('Any', typing.Any), ('Optional', typing.Optional)]:
    setattr(builtins, a, v)

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["OPENCV_LOG_LEVEL"] = "ERROR"

current_dir = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / "agent_bridge"))
sys.path.insert(0, str(current_dir / "prizolov_sports_ai"))

# CV Mock
try: import cv2
except:
    from types import ModuleType
    m=ModuleType("cv2")
    for x in ['COLOR_BGR2GRAY','COLOR_BGR2YCrCb','COLOR_YCrCb2BGR','INTER_CUBIC','INTER_NEAREST','THRESH_BINARY_INV','THRESH_OTSU','IMWRITE_JPEG_QUALITY','INPAINT_NS']: setattr(m,x,0)
    for f in ['VideoCapture','resize','cvtColor','threshold','inRange','line','putText','imwrite','undistortPoints','undistort','getOptimalNewCameraMatrix']: setattr(m,f,lambda *a,**k:(None if f=='getOptimalNewCameraMatrix' else (0.0,a[0] if a else None)))
    sys.modules["cv2"]=m

def compile_proto():
    try:
        from grpc_tools import protoc
        p=current_dir/"proto"/"prizolov_agent.proto"
        o=current_dir/"agent_bridge"
        if p.exists():
            o.mkdir(parents=True, exist_ok=True)
            protoc.main(["grpc_tools.protoc", f"--proto_path={p.parent}", f"--python_out={o}", f"--grpc_python_out={o}", str(p)])
            g=o/"prizolov_agent_pb2_grpc.py"
            if g.exists(): g.write_text(g.read_text(encoding="utf-8").replace("from . import prizolov_agent_pb2","import prizolov_agent_pb2"), encoding="utf-8")
    except Exception as e: logging.warning(f"⚠️ Proto skipped: {e}")
compile_proto()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger=logging.getLogger("PrizolovSportsAI.Main")
keep_running=True
signal.signal(signal.SIGINT, lambda s,f: setattr(__import__('__main__'),'keep_running',False))
signal.signal(signal.SIGTERM, lambda s,f: setattr(__import__('__main__'),'keep_running',False))

# === ИМПОРТЫ С FALLBACK ===
try:
    from core.orchestrator import PrizolovSportsOrchestrator
    from core.admin_dashboard import start_dashboard_server
    from modules.event_discovery import EventDiscoveryEngine
except ImportError:
    try:
        from prizolov_sports_ai.core.orchestrator import PrizolovSportsOrchestrator
        from prizolov_sports_ai.core.admin_dashboard import start_dashboard_server
        from prizolov_sports_ai.modules.event_discovery import EventDiscoveryEngine
    except ImportError:
        EventDiscoveryEngine=None

# === FALLBACK DISCOVERY ===
class FallbackDiscovery:
    def __init__(self): self._e=[]
    async def start_auto_discovery(self): await self._fetch()
    def stop(self): pass
    async def _fetch(self):
        now=datetime.datetime.utcnow()
        sp=[("football",["РПЛ","АПЛ"],["Спартак","Зенит","Реал","Барса"]),
            ("hockey",["КХЛ","НХЛ"],["ЦСКА","СКА","Тампа","Колорадо"]),
            ("basketball",["ВТБ","НБА"],["ЦСКА","УНИКС","Лейкерс","Бостон"])]
        self._e=[]
        for sport,leagues,teams in sp:
            for i in range(2):
                self._e.append({"match_id":f"{sport}_{i}_{random.randint(100,999)}","sport":sport,"league":random.choice(leagues),
                                "home_team":random.choice(teams),"away_team":random.choice([t for t in teams if t!=random.choice(teams)]),
                                "start_time":now.isoformat(),"status":"live","betting_interest":0.85})
    def get_events_for_analysis(self,**k): return self._e
    def get_all_events(self): return self._e

async def main_loop(host:str, port:int, mock:bool):
    global keep_running
    logger.info("🔄 Инициализация пайплайна v8.52...")
    
    # === ИСПРАВЛЕНО: Убраны лишние скобки () после вызова конструктора ===
    disc = EventDiscoveryEngine(refresh_interval=45) if EventDiscoveryEngine else FallbackDiscovery()
    await disc.start_auto_discovery()
    logger.info(f"✅ Discovery ready. Events: {len(disc.get_all_events())}")

    orch = PrizolovSportsOrchestrator(target_agent_host=host, mock_mode=mock, discovery_engine=disc)
    await start_dashboard_server(orch, port=port)
    logger.info("🌐 WebSocket Dashboard active")

    await orch.run_initial_analysis()
    
    try:
        while keep_running:
            await orch.run_continuous_scan()
            await asyncio.sleep(45)
    finally:
        await orch.shutdown()

if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--agent_host", default="localhost:50051")
    p.add_argument("--dashboard_port", type=int, default=8080)
    p.add_argument("--mock-mode", action="store_true")
    # Deprecated args (для совместимости с Amvera/старыми конфигами)
    p.add_argument("--sport", type=str, default=None, help="[DEPRECATED]")
    p.add_argument("--match_id", type=str, default=None, help="[DEPRECATED]")
    p.add_argument("--weights", type=str, default=None, help="[DEPRECATED]")
    
    args, unknown = p.parse_known_args()
    
    if args.sport or args.match_id:
        logger.warning(f"⚠️ Deprecated args ignored: sport={args.sport}, match_id={args.match_id}. Using autonomous discovery.")
    
    try: 
        asyncio.run(main_loop(args.agent_host, args.dashboard_port, args.mock_mode))
    except KeyboardInterrupt: 
        logger.info("👋 Shutdown.")
