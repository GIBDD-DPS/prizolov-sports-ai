#!/usr/bin/env python3
# ============================================
# Prizolov Sports AI - Main Execution Engine
# Version: 7.00 (+1.00: Legacy CV Loop Removal & Strict Discovery Pipeline)
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
import typing

# Глобальная инжекция типов
import builtins
setattr(builtins, 'Path', pathlib.Path)
setattr(builtins, 'Tuple', typing.Tuple)
setattr(builtins, 'List', typing.List)
setattr(builtins, 'Dict', typing.Dict)
setattr(builtins, 'Any', typing.Any)
setattr(builtins, 'Optional', typing.Optional)

# Глушение GUI-артефактов
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["OPENCV_LOG_LEVEL"] = "ERROR"

# Настройка путей
current_dir = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / "agent_bridge"))
sys.path.insert(0, str(current_dir / "prizolov_sports_ai"))

# Безопасный Monkey Patching для cv2
try:
    import cv2
except Exception:
    from types import ModuleType
    mock_cv2 = ModuleType("cv2")
    for attr in ['COLOR_BGR2GRAY','COLOR_BGR2YCrCb','COLOR_YCrCb2BGR','INTER_CUBIC','INTER_NEAREST',
                 'THRESH_BINARY_INV','THRESH_OTSU','IMWRITE_JPEG_QUALITY','INPAINT_NS']:
        setattr(mock_cv2, attr, 0)
    for fn in ['VideoCapture','resize','cvtColor','threshold','inRange','line','putText','imwrite','undistortPoints','undistort','getOptimalNewCameraMatrix']:
        setattr(mock_cv2, fn, lambda *a, **k: (None if fn=='getOptimalNewCameraMatrix' else (0.0, a[0] if a else None)))
    sys.modules["cv2"] = mock_cv2

def compile_proto_on_the_fly():
    try:
        from grpc_tools import protoc
        proto_file = current_dir / "proto" / "prizolov_agent.proto"
        out_bridge_dir = current_dir / "agent_bridge"
        if proto_file.exists():
            out_bridge_dir.mkdir(parents=True, exist_ok=True)
            protoc.main([
                "grpc_tools.protoc", f"--proto_path={proto_file.parent}",
                f"--python_out={out_bridge_dir}", f"--grpc_python_out={out_bridge_dir}", str(proto_file)
            ])
            grpc_file = out_bridge_dir / "prizolov_agent_pb2_grpc.py"
            if grpc_file.exists():
                content = grpc_file.read_text(encoding="utf-8")
                grpc_file.write_text(content.replace("from . import prizolov_agent_pb2", "import prizolov_agent_pb2"), encoding="utf-8")
    except Exception as e:
        logging.warning(f"⚠️ Proto compilation skipped: {e}")

compile_proto_on_the_fly()

# Импорт ядра
try:
    from core.orchestrator import PrizolovSportsOrchestrator
    from core.admin_dashboard import start_dashboard_server
    from core.s3_backup import S3CloudBackupHub
    from modules.event_discovery import EventDiscoveryEngine
except ModuleNotFoundError:
    from prizolov_sports_ai.core.orchestrator import PrizolovSportsOrchestrator
    from prizolov_sports_ai.core.admin_dashboard import start_dashboard_server
    from prizolov_sports_ai.core.s3_backup import S3CloudBackupHub
    from prizolov_sports_ai.modules.event_discovery import EventDiscoveryEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("PrizolovSportsAI.Main")
keep_running = True

def handle_exit_signal(signum, frame):
    global keep_running
    keep_running = False

signal.signal(signal.SIGINT, handle_exit_signal)
signal.signal(signal.SIGTERM, handle_exit_signal)

async def main_inference_loop(host: str, dashboard_port: int, mock_mode: bool, discovery_interval: int):
    global keep_running
    logger.info("=== Запуск автономного AI-конвейера Prizolov Sports v7.00 ===")
    
    discovery = EventDiscoveryEngine(refresh_interval=discovery_interval)
    asyncio.create_task(discovery.start_auto_discovery())
    logger.info("🌍 Event Discovery Engine запущен")

    orchestrator = PrizolovSportsOrchestrator(target_agent_host=host, mock_mode=mock_mode, discovery_engine=discovery)
    await start_dashboard_server(orchestrator, port=dashboard_port)

    try:
        s3_hub = S3CloudBackupHub()
        asyncio.create_task(s3_hub.run_periodic_backup_loop(base_data_dir="/data", interval_seconds=600))
    except Exception as e:
        logger.warning(f"⚠️ S3 Backup skipped: {e}")

    try:
        await orchestrator.run_continuous_scan(keep_running_ref=lambda: keep_running)
    finally:
        await orchestrator.shutdown()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent_host", type=str, default="localhost:50051")
    parser.add_argument("--dashboard_port", type=int, default=8080)
    parser.add_argument("--mock-mode", action="store_true", help="Run in mock mode")
    parser.add_argument("--discovery-interval", type=int, default=120)
    args = parser.parse_args()

    try:
        asyncio.run(main_inference_loop(args.agent_host, args.dashboard_port, args.mock_mode, args.discovery_interval))
    except KeyboardInterrupt:
        logger.info("👋 Завершение работы...")
