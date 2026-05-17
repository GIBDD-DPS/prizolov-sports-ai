#!/usr/bin/env python3
# ============================================
# Prizolov Sports AI - Main Execution Engine
# Version: 3.06 (Native On-the-Fly Protobuf Compiler)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at prizolov.ru
# ============================================

import sys
import os
from pathlib import Path

# 1. Жесткое перестроение путей поиска модулей для Amvera Cloud environment
current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / "prizolov_sports_ai"))

# 2. Автоматическая компиляция .proto контрактов внутри контейнера Amvera при старте
def compile_proto_on_the_fly():
    try:
        from grpc_tools import protoc
        proto_file = current_dir / "proto" / "prizolov_agent.proto"
        out_bridge_dir = current_dir / "agent_bridge"
        
        # Проверяем существование исходной директории контракта
        if proto_file.exists():
            out_bridge_dir.mkdir(parents=True, exist_ok=True)
            
            # Конфигурируем аргументы сборщика под flat-структуру Amvera
            protoc_args = [
                "grpc_tools.protoc",
                f"--proto_path={proto_file.parent}",
                f"--python_out={out_bridge_dir}",
                f"--grpc_python_out={out_bridge_dir}",
                str(proto_file)
            ]
            exit_code = protoc.main(protoc_args)
            
            if exit_code == 0:
                # Патчинг импортов в сгенерированном gRPC файле под прямые локальные вызовы
                grpc_file = out_bridge_dir / "prizolov_agent_pb2_grpc.py"
                if grpc_file.exists():
                    with open(grpc_file, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    broken_import = "import prizolov_agent_pb2 as prizolov__agent__pb2"
                    fixed_import = "from . import prizolov_agent_pb2 as prizolov__agent__pb2"
                    
                    if broken_import in content:
                        content = content.replace(broken_import, fixed_import)
                        with open(grpc_file, "w", encoding="utf-8") as f:
                            f.write(content)
    except Exception as e:
        # Не блокируем старт, если файлы уже были скомпилированы локально
        pass

# Запускаем сборку интерфейсов до импорта оркестратора
compile_proto_on_the_fly()

import argparse
import asyncio
import signal
import logging
import random

# Отказоустойчивый импорт оркестратора
try:
    from core.orchestrator import PrizolovSportsOrchestrator
except ModuleNotFoundError:
    from prizolov_sports_ai.core.orchestrator import PrizolovSportsOrchestrator

# Настройка логирования для контейнеров Amvera Cloud
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("PrizolovSportsAI.Main")

# Переменная контроля жизненного цикла приложения
keep_running = True

def handle_exit_signal(signum, frame):
    """Перехват сигналов завершения для безопасной остановки процессов"""
    global keep_running
    logger.info(f"Получен системный сигнал остановки ({signum}). Завершение работы...")
    keep_running = False

signal.signal(signal.SIGINT, handle_exit_signal)
signal.signal(signal.SIGTERM, handle_exit_signal)

async def main_inference_loop(sport: str, match_id: str, host: str):
    """Главный цикл инференса нейросетей и стриминга аналитики"""
    global keep_running
    
    logger.info("=== Инициализация Prizolov Sports AI Engine ===")
    orchestrator = PrizolovSportsOrchestrator(target_agent_host=host)
    
    # Запуск оркестратора и gRPC-клиента под выбранный матч
    await orchestrator.initialize_match(match_id=match_id, sport=sport)
    
    initial_protocol = {"score_a": 0, "score_b": 0}
    orchestrator.update_official_protocol(initial_protocol)
    
    elapsed_seconds = 0
    total_match_seconds = 5400 if sport == "football" else (3600 if sport == "hockey" else 2400)
    
    logger.info(f"Конвейер инференса запущен. Обработка потока для спорта: {sport}...")
    
    try:
        while keep_running:
            elapsed_seconds += 1
            time_left_ratio = max(0.0, 1.0 - (elapsed_seconds / total_match_seconds))
            
            minutes = elapsed_seconds // 60
            seconds = elapsed_seconds % 60
            game_time_str = f"{minutes:02d}:{seconds:02d}"
            
            if elapsed_seconds % 90 == 0:
                live_protocol = {
                    "score_a": random.choices([0, 1], weights=[0.9, 0.1])[0] + orchestrator.active_module.current_score_a,
                    "score_b": random.choices([0, 1], weights=[0.93, 0.07])[0] + orchestrator.active_module.current_score_b
                }
                if sport == "football":
                    live_protocol["corners_a"] = orchestrator.active_module.corners_a + random.choice([0, 1])
                    live_protocol["corners_b"] = orchestrator.active_module.corners_b + random.choice([0, 1])
                elif sport == "hockey":
                    live_protocol["shots_a"] = orchestrator.active_module.shots_a + random.choice([0, 1, 2])
                    live_protocol["shots_b"] = orchestrator.active_module.shots_b + random.choice([0, 1, 2])
                
                orchestrator.update_official_protocol(live_protocol)
                logger.info(f"[Protocol Update] Текущий счет матча: {live_protocol['score_a']}:{live_protocol['score_b']}")

            mock_tracking_data = {
                "ball_x": round(random.uniform(0.0, 100.0), 2),
                "ball_y": round(random.uniform(0.0, 50.0), 2),
                "ball_owner_team": random.choice(["A", "B", None]),
                "recent_dominance_ratio": random.uniform(0.4, 0.65),
                "live_xg_a": round(orchestrator.active_module.current_score_a + random.uniform(0.0, 0.5), 2),
                "live_xg_b": round(orchestrator.active_module.current_score_b + random.uniform(0.0, 0.4), 2),
                "danger_attacks_a": int(elapsed_seconds * 0.15),
                "danger_attacks_b": int(elapsed_seconds * 0.12)
            }

            await orchestrator.process_cv_frame(
                tracking_data=mock_tracking_data,
                game_time_str=game_time_str,
                time_left_ratio=time_left_ratio,
                elapsed_seconds=elapsed_seconds
            )
            
            await asyncio.sleep(0.05)
            
            if time_left_ratio <= 0:
                logger.info("Матч завершен по времени. Завершение работы конвейера.")
                break

    except Exception as e:
        logger.critical(f"Критическая ошибка основного цикла инференса: {e}")
    finally:
        await orchestrator.shutdown()
        logger.info("=== Модуль Prizolov Sports AI успешно выгружен из системы ===")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prizolov Sports AI Production Runner")
    parser.add_argument("--sport", type=str, required=True, help="Вид спорта: football, hockey, basketball...")
    parser.add_argument("--match_id", type=str, default="live_match_001", help="Уникальный строковый ID матча")
    parser.add_argument("--agent_host", type=str, default="localhost:50051", help="Адрес gRPC сервера Prizolov Agent OS")
    
    args = parser.parse_args()
    
    try:
        asyncio.run(main_inference_loop(sport=args.sport, match_id=args.match_id, host=args.agent_host))
    except KeyboardInterrupt:
        pass
