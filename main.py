#!/usr/bin/env python3
# ============================================
# Prizolov Sports AI - Main Execution Engine
# Version: 3.03 (Strict Pre-Import Path Injection)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at prizolov.ru
# ============================================

import sys
import os
from pathlib import Path

# Внедряем пути строго до выполнения любых локальных импортов проекта
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))
if str(current_dir.parent) not in sys.path:
    sys.path.insert(0, str(current_dir.parent))

import argparse
import asyncio
import signal
import logging
import random  # Для демонстрационной генерации CV-данных в отсутствие реальной камеры

# Импортируем локальные модули только после инжекции путей в sys.path
from prizolov_sports_ai.core.orchestrator import PrizolovSportsOrchestrator

# Настройка логирования для контейнеров Docker / Systemd
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

# Регистрируем обработчики для корректного закрытия в докере
signal.signal(signal.SIGINT, handle_exit_signal)
signal.signal(signal.SIGTERM, handle_exit_signal)

async def main_inference_loop(sport: str, match_id: str, host: str):
    """Главный цикл инференса нейросетей и стриминга аналитики"""
    global keep_running
    
    logger.info("=== Инициализация Prizolov Sports AI Engine ===")
    orchestrator = PrizolovSportsOrchestrator(target_agent_host=host)
    
    # 1. Запуск оркестратора и gRPC-клиента под выбранный матч
    await orchestrator.initialize_match(match_id=match_id, sport=sport)
    
    # Имитируем стартовый протокол матча (счет 0:0)
    initial_protocol = {"score_a": 0, "score_b": 0}
    orchestrator.update_official_protocol(initial_protocol)
    
    # Тайминги для симуляции игры (для продакшена здесь подключается OpenCV VideoCapture/RTSP)
    elapsed_seconds = 0
    total_match_seconds = 5400 if sport == "football" else (3600 if sport == "hockey" else 2400)
    
    logger.info(f"Конвейер инференса запущен. Обработка потока для спорта: {sport}...")
    
    try:
        while keep_running:
            # 2. Симуляция получения обработанных данных с YOLOv10 / RTMPose (CV-слой)
            elapsed_seconds += 1
            time_left_ratio = max(0.0, 1.0 - (elapsed_seconds / total_match_seconds))
            
            # Рассчитываем строковое отображение игрового времени
            minutes = elapsed_seconds // 60
            seconds = elapsed_seconds % 60
            game_time_str = f"{minutes:02d}:{seconds:02d}"
            
            # Раз в минуту имитируем случайное изменение официального счета или статистики
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

            # Формируем сырой пакет пространственных данных от детектора
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

            # 3. Передача CV-данных в оркестратор для генерации и отправки линии в Agent OS
            await orchestrator.process_cv_frame(
                tracking_data=mock_tracking_data,
                game_time_str=game_time_str,
                time_left_ratio=time_left_ratio,
                elapsed_seconds=elapsed_seconds
            )
            
            # Эмуляция частоты обработки ~20 кадров/пакетов аналитики в секунду
            await asyncio.sleep(0.05)
            
            if time_left_ratio <= 0:
                logger.info("Матч завершен по времени. Завершение работы конвейера.")
                break

    except Exception as e:
        logger.critical(f"Критическая ошибка основного цикла инференса: {e}")
    finally:
        # 4. Освобождение ресурсов и отключение gRPC каналов при выходе
        await orchestrator.shutdown()
        logger.info("=== Модуль Prizolov Sports AI успешно выгружен из системы ===")

if __name__ == "__main__":
    # Настройка парсера аргументов командной строки
    parser = argparse.ArgumentParser(description="Prizolov Sports AI Production Runner")
    parser.add_argument("--sport", type=str, required=True, help="Вид спорта: football, hockey, basketball, теннис и т.д.")
    parser.add_argument("--match_id", type=str, default="live_match_001", help="Уникальный строковый ID матча")
    parser.add_argument("--agent_host", type=str, default="localhost:50051", help="Адрес gRPC сервера Prizolov Agent OS")
    
    args = parser.parse_args()
    
    # Запуск асинхронной среды исполнения
    try:
        asyncio.run(main_inference_loop(sport=args.sport, match_id=args.match_id, host=args.agent_host))
    except KeyboardInterrupt:
        pass
