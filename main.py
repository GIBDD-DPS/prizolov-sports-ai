#!/usr/bin/env python3
# ============================================
# Prizolov Sports AI - Main Execution Engine
# Version: 6.16 (+1.01: Autonomous Event Discovery Integration & Dynamic Pipeline)
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

# Настройка путей поиска модулей
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
    mock_cv2.COLOR_BGR2GRAY = 6
    mock_cv2.COLOR_BGR2YCrCb = 36
    mock_cv2.COLOR_YCrCb2BGR = 38
    mock_cv2.INTER_CUBIC = 2
    mock_cv2.INTER_NEAREST = 0
    mock_cv2.THRESH_BINARY_INV = 1
    mock_cv2.THRESH_OTSU = 8
    mock_cv2.IMWRITE_JPEG_QUALITY = 1
    mock_cv2.INPAINT_NS = 0
    mock_cv2.VideoCapture = lambda *args, **kwargs: None
    mock_cv2.resize = lambda src, dsize, *args, **kwargs: src
    mock_cv2.cvtColor = lambda src, code, *args, **kwargs: src
    mock_cv2.threshold = lambda src, thresh, maxval, type, *args, **kwargs: (0.0, src)
    mock_cv2.inRange = lambda src, lowerb, upperb, *args, **kwargs: src
    mock_cv2.line = lambda img, pt1, pt2, color, *args, **kwargs: img
    mock_cv2.putText = lambda img, text, org, fontFace, fontScale, color, *args, **kwargs: img
    mock_cv2.imwrite = lambda filename, img, *args, **kwargs: True
    mock_cv2.undistortPoints = lambda src, cameraMatrix, distCoeffs, *args, **kwargs: src
    mock_cv2.undistort = lambda src, cameraMatrix, distCoeffs, *args, **kwargs: src
    mock_cv2.getOptimalNewCameraMatrix = lambda cameraMatrix, distCoeffs, imageSize, alpha, *args, **kwargs: (cameraMatrix, (0,0,0,0))
    sys.modules["cv2"] = mock_cv2

def compile_proto_on_the_fly():
    try:
        from grpc_tools import protoc
        proto_file = current_dir / "proto" / "prizolov_agent.proto"
        out_bridge_dir = current_dir / "agent_bridge"
        if proto_file.exists():
            out_bridge_dir.mkdir(parents=True, exist_ok=True)
            protoc_args = [
                "grpc_tools.protoc", f"--proto_path={proto_file.parent}",
                f"--python_out={out_bridge_dir}", f"--grpc_python_out={out_bridge_dir}",
                str(proto_file)
            ]
            exit_code = protoc.main(protoc_args)
            if exit_code == 0:
                grpc_file = out_bridge_dir / "prizolov_agent_pb2_grpc.py"
                if grpc_file.exists():
                    with open(grpc_file, "r", encoding="utf-8") as f:
                        content = f.read()
                    content = content.replace("from . import prizolov_agent_pb2", "import prizolov_agent_pb2")
                    with open(grpc_file, "w", encoding="utf-8") as f:
                        f.write(content)
    except Exception as e:
        logging.warning(f"⚠️ Proto compilation skipped: {e}")

compile_proto_on_the_fly()

# Безопасный импорт ядра
try:
    from core.orchestrator import PrizolovSportsOrchestrator
    from core.admin_dashboard import start_dashboard_server
    from core.s3_backup import S3CloudBackupHub
    from modules.event_discovery import EventDiscoveryEngine
except ModuleNotFoundError:
    try:
        from prizolov_sports_ai.core.orchestrator import PrizolovSportsOrchestrator
        from prizolov_sports_ai.core.admin_dashboard import start_dashboard_server
        from prizolov_sports_ai.core.s3_backup import S3CloudBackupHub
        from prizolov_sports_ai.modules.event_discovery import EventDiscoveryEngine
    except ImportError:
        logging.critical("❌ Core modules not found. Exiting.")
        sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("PrizolovSportsAI.Main")
keep_running = True

def handle_exit_signal(signum, frame):
    global keep_running
    keep_running = False

signal.signal(signal.SIGINT, handle_exit_signal)
signal.signal(signal.SIGTERM, handle_exit_signal)

async def main_inference_loop(sport: str, match_id: str, host: str, dashboard_port: int, mock_mode: bool, discovery_interval: int):
    global keep_running
    logger.info("=== Запуск автономного AI-конвейера Prizolov Sports ===")
    
    # 1. Инициализация движка поиска событий
    discovery = EventDiscoveryEngine(refresh_interval=discovery_interval)
    asyncio.create_task(discovery.start_auto_discovery())
    logger.info("🌍 Event Discovery Engine запущен в фоне")

    # 2. Инициализация оркестратора с передачей движка поиска
    orchestrator = PrizolovSportsOrchestrator(
        target_agent_host=host, 
        mock_mode=mock_mode,
        discovery_engine=discovery
    )

    # 3. Запуск WebSocket-дашборда
    await start_dashboard_server(orchestrator, port=dashboard_port)

    # 4. Инициализация S3-бэкапов
    try:
        s3_hub = S3CloudBackupHub()
        asyncio.create_task(s3_hub.run_periodic_backup_loop(base_data_dir="/data", interval_seconds=600))
    except Exception as e:
        logger.warning(f"⚠️ S3 Backup initialization skipped: {e}")

    # 5. Запуск непрерывного цикла сканирования и анализа
    try:
        await orchestrator.run_continuous_scan(keep_running_ref=lambda: keep_running)
    finally:
        await orchestrator.shutdown()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sport", type=str, required=False, default="auto")
    parser.add_argument("--match_id", type=str, default="auto_discovery")
    parser.add_argument("--agent_host", type=str, default="localhost:50051")
    parser.add_argument("--dashboard_port", type=int, default=8080)
    parser.add_argument("--mock-mode", action="store_true", help="Run in mock mode")
    parser.add_argument("--discovery-interval", type=int, default=120, help="Секунды между обновлениями списка событий")
    args = parser.parse_args()

    try:
        asyncio.run(main_inference_loop(
            args.sport, args.match_id, args.agent_host, 
            args.dashboard_port, args.mock_mode, args.discovery_interval
        ))
    except KeyboardInterrupt:
        logger.info("👋 Получен сигнал прерывания, завершаем работу...")
