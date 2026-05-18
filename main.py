#!/usr/bin/env python3
# ============================================
# Prizolov Sports AI - Main Execution Engine
# Version: 5.08 (Forced Headless Simulation Core)
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
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Жесткое отключение оконных GUI-систем на уровне Linux
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["OPENCV_LOG_LEVEL"] = "ERROR"

current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / "agent_bridge"))
sys.path.insert(0, str(current_dir / "prizolov_sports_ai"))

def compile_proto_on_the_fly():
    try:
        from grpc_tools import protoc
        proto_file = current_dir / "proto" / "prizolov_agent.proto"
        out_bridge_dir = current_dir / "agent_bridge"
        
        if proto_file.exists():
            out_bridge_dir.mkdir(parents=True, exist_ok=True)
            protoc_args = [
                "grpc_tools.protoc",
                f"--proto_path={proto_file.parent}",
                f"--python_out={out_bridge_dir}",
                f"--grpc_python_out={out_bridge_dir}",
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
    except Exception:
        pass

compile_proto_on_the_fly()

YOLO = None
try:
    from ultralytics import YOLO
except Exception:
    pass

try:
    from core.orchestrator import PrizolovSportsOrchestrator
    from core.admin_dashboard import start_dashboard_server
    from core.s3_backup import S3CloudBackupHub
except ModuleNotFoundError:
    from prizolov_sports_ai.core.orchestrator import PrizolovSportsOrchestrator
    from prizolov_sports_ai.core.admin_dashboard import start_dashboard_server
    from prizolov_sports_ai.core.s3_backup import S3CloudBackupHub

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("PrizolovSportsAI.Main")
keep_running = True

def handle_exit_signal(signum, frame):
    global keep_running
    logger.info(f"Получен системный сигнал остановки ({signum}). Завершение работы...")
    keep_running = False

signal.signal(signal.SIGINT, handle_exit_signal)
signal.signal(signal.SIGTERM, handle_exit_signal)

async def main_inference_loop(sport: str, match_id: str, host: str, video_source: str, weights_path: str, dashboard_port: int):
    global keep_running
    logger.info("=== Запуск мультиканального ИИ-движка Prizolov Sports ===")
    
    orchestrator = PrizolovSportsOrchestrator(target_agent_host=host)
    await orchestrator.initialize_match(match_id=match_id, sport=sport)
    
    # Сразу поднимаем WebSocket-сервер вещания на порту 8080 для Elementor
    await start_dashboard_server(orchestrator, port=dashboard_port)
    
    s3_hub = S3CloudBackupHub()
    persistent_dir = os.getenv("PERSISTENT_DATA_DIR", "/data")
    asyncio.create_task(s3_hub.run_periodic_backup_loop(base_data_dir=persistent_dir, interval_seconds=600))
    
    initial_protocol = {"score_a": 0, "score_b": 0}
    orchestrator.update_official_protocol(match_id, initial_protocol)

    # Изолированный математический генератор симуляции матча
    # Снабжает WordPress виджет координатами и азиатскими котировками в обход libGL ошибки
    logger.warning("[Mode Sync] Физический OpenCV плеер отключен. Активирован отладочный Live-генератор.")
    frame_count = 0
    fps = 25.0
    frame_delay = 1.0 / fps
    total_match_seconds = 5400 if sport == "football" else (3600 if sport == "hockey" else 2400)
    
    try:
        while keep_running:
            start_time = time.time()
            frame_count += 1
            elapsed_seconds = int(frame_count / fps)
            time_left_ratio = max(0.0, 1.0 - (elapsed_seconds / total_match_seconds))
            game_time_str = f"{elapsed_seconds // 60:02d}:{elapsed_seconds % 60:02d}"

            tracking_data = {
                "ball_x": 52.5 + (frame_count % 30) * 0.1, 
                "ball_y": 34.0 + (frame_count % 15) * 0.05, 
                "ball_owner_team": "A" if frame_count % 40 < 20 else "B",
                "recent_dominance_ratio": 0.54, 
                "live_xg_a": 0.01 * (frame_count % 5), 
                "live_xg_b": 0.02,
                "danger_attacks_a": 3, 
                "danger_attacks_b": 2
            }

            await orchestrator.process_cv_frame(
                match_id=match_id,
                tracking_data=tracking_data,
                game_time_str=game_time_str,
                time_left_ratio=time_left_ratio,
                elapsed_seconds=elapsed_seconds
            )

            if time_left_ratio <= 0:
                break
                
            process_duration = time.time() - start_time
            await asyncio.sleep(max(0.0, frame_delay - process_duration))
    finally:
        await orchestrator.shutdown()
        logger.info("=== Симуляционный live-генератор успешно завершил сессию ===")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prizolov Sports AI Runner")
    parser.append_argument("--sport", type=str, required=True)
    parser.add_argument("--match_id", type=str, default="live_match_001")
    parser.add_argument("--agent_host", type=str, default="localhost:50051")
    parser.add_argument("--video_source", type=str, default="0")
    parser.add_argument("--weights", type=str, default="/data/yolov10_sports.pt")
    parser.add_argument("--dashboard_port", type=int, default=8080)
    
    args = parser.parse_args()
    try:
        asyncio.run(main_inference_loop(
            sport=args.sport, match_id=args.match_id, host=args.agent_host, 
            video_source=args.video_source, weights_path=args.weights,
            dashboard_port=args.dashboard_port
        ))
    except KeyboardInterrupt:
        pass
