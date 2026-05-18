#!/usr/bin/env python3
# ============================================
# Prizolov Sports AI - Main Execution Engine
# Version: 5.02 (Live Dashboard Activation Core)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at cloud.amvera.ru
# ============================================

import sys
import os
from pathlib import Path

# 1. Жесткое перестроение путей поиска модулей для Amvera Cloud environment
current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / "agent_bridge"))
sys.path.insert(0, str(current_dir / "prizolov_sports_ai"))

# 2. Автоматическая компиляция .proto контрактов внутри контейнера Amvera при старте
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

import argparse
import asyncio
import signal
import logging
import time
from concurrent.futures import ThreadPoolExecutor

# Нативные CV-зависимости
import cv2
try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

# Импорт локальных компонентов архитектуры
try:
    from core.orchestrator import PrizolovSportsOrchestrator
    from core.admin_dashboard import start_dashboard_server
except ModuleNotFoundError:
    from prizolov_sports_ai.core.orchestrator import PrizolovSportsOrchestrator
    from prizolov_sports_ai.core.admin_dashboard import start_dashboard_server

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

def run_yolo_inference(model, frame) -> list:
    """Выполнение инференса YOLOv10 в отдельном синхронном потоке"""
    if model is None:
        return []
    results = model.track(frame, persist=True, verbose=False)
    return results

async def main_inference_loop(sport: str, match_id: str, host: str, video_source: str, weights_path: str, dashboard_port: int):
    global keep_running
    logger.info("=== Инициализация Prizolov Sports AI Engine ===")
    
    orchestrator = PrizolovSportsOrchestrator(target_agent_host=host)
    
    # 1. Запуск оркестратора под выбранный матч
    await orchestrator.initialize_match(match_id=match_id, sport=sport)
    
    # 2. Исправлено: Активация Live-админ-панели управления в продакшене Amvera Cloud
    await start_dashboard_server(orchestrator, port=dashboard_port)
    
    # Инициализация стартового протокола
    initial_protocol = {"score_a": 0, "score_b": 0}
    orchestrator.update_official_protocol(initial_protocol)
    
    # 3. Загрузка весов YOLOv10 (из папки постоянных данных /data)
    yolo_model = None
    if YOLO and weights_path and os.path.exists(weights_path):
        logger.info(f"Загрузка весов YOLOv10 для {sport} из: {weights_path}")
        yolo_model = YOLO(weights_path)
    else:
        logger.warning("Модель YOLOv10 не загружена (отсутствуют веса или библиотека). Включен фолбэк-анализатор.")

    # 4. Подключение к источнику трансляции (RTSP / RTMP / MP4)
    logger.info(f"Открытие live-трансляции: {video_source}")
    cap = cv2.VideoCapture(video_source if not video_source.isdigit() else int(video_source))
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
    
    if not cap.isOpened():
        logger.error(f"Критическая ошибка: Не удалось открыть видеопоток {video_source}")
        await orchestrator.shutdown()
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0: fps = 25.0
    frame_delay = 1.0 / fps
    
    executor = ThreadPoolExecutor(max_workers=1)
    loop = asyncio.get_running_loop()
    
    frame_count = 0
    total_match_seconds = 5400 if sport == "football" else (3600 if sport == "hockey" else 2400)
    
    logger.info("Компьютерное зрение инициализировано. Старт обработки трансляции...")

    try:
        while keep_running and cap.isOpened():
            start_time = time.time()
            
            ret, frame = cap.read()
            if not ret:
                logger.warning("Потеря сигнала. Попытка восстановить подключение к трансляции...")
                await asyncio.sleep(2)
                cap.open(video_source if not video_source.isdigit() else int(video_source))
                continue

            frame_count += 1
            elapsed_seconds = int(frame_count / fps)
            time_left_ratio = max(0.0, 1.0 - (elapsed_seconds / total_match_seconds))
            game_time_str = f"{elapsed_seconds // 60:02d}:{elapsed_seconds % 60:02d}"

            tracking_data = {
                "ball_x": 0.0, "ball_y": 0.0, "ball_owner_team": None,
                "recent_dominance_ratio": 0.5, "live_xg_a": 0.0, "live_xg_b": 0.0,
                "danger_attacks_a": 0, "danger_attacks_b": 0
            }

            # 5. Асинхронный вызов инференса YOLOv10
            if yolo_model:
                results = await loop.run_in_executor(executor, run_yolo_inference, yolo_model, frame)
                
                if results and len(results) > 0:
                    boxes = results.boxes
                    for box in boxes:
                        cls_id = int(box.cls)
                        xyxy = box.xyxy.tolist()
                        
                        if cls_id == 0:
                            tracking_data["ball_x"] = (xyxy + xyxy) / 2.0
                            tracking_data["ball_y"] = (xyxy + xyxy) / 2.0
                            tracking_data["puck_visible"] = True
                            tracking_data["puck_x"] = tracking_data["ball_x"]
                            tracking_data["puck_y"] = tracking_data["ball_y"]

            await orchestrator.process_cv_frame(
                tracking_data=tracking_data,
                game_time_str=game_time_str,
                time_left_ratio=time_left_ratio,
                elapsed_seconds=elapsed_seconds
            )

            process_duration = time.time() - start_time
            await asyncio.sleep(max(0.0, frame_delay - process_duration))

    except Exception as e:
        logger.critical(f"Сбой в цикле инференса видеопотока: {e}")
    finally:
        cap.release()
        executor.shutdown()
        await orchestrator.shutdown()
        logger.info("=== Модуль Prizolov Sports AI успешно выгружен из системы ===")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prizolov Sports AI Production Runner")
    parser.add_argument("--sport", type=str, required=True, help="football, hockey, basketball...")
    parser.add_argument("--match_id", type=str, default="live_match_001", help="ID матча")
    parser.add_argument("--agent_host", type=str, default="localhost:50051", help="Адрес Agent OS")
    parser.add_argument("--video_source", type=str, default="0", help="RTSP/RTMP ссылка, путь к mp4 или ID веб-камеры")
    parser.add_argument("--weights", type=str, default="/data/yolov10_sports.pt", help="Путь к файлу весов YOLOv10")
    # Добавлен аргумент конфигурирования порта админ-панели
    parser.add_argument("--dashboard_port", type=int, default=8080, help="Сетевой порт для Live панели управления скаута")
    
    args = parser.parse_args()
    try:
        asyncio.run(main_inference_loop(
            sport=args.sport, match_id=args.match_id, host=args.agent_host, 
            video_source=args.video_source, weights_path=args.weights,
            dashboard_port=args.dashboard_port
        ))
    except KeyboardInterrupt:
        pass
