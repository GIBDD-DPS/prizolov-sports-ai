#!/usr/bin/env python3
# ============================================
# Prizolov Sports AI - High-Load gRPC Stress Tester
# Version: 4.01 (Initial Architecture Release)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production latency & throughput tests
# ============================================

import sys
import os
import asyncio
import logging
import time
from pathlib import Path
from concurrent import futures

import grpc

# Определение корней проекта и инжекция путей под flat-структуру Amvera
current_dir = Path(__file__).resolve().parent
root_dir = current_dir.parent
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(root_dir / "agent_bridge"))

import prizolov_agent_pb2
import prizolov_agent_pb2_grpc

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("PrizolovSportsAI.StressTester")

class MockSportsAnalyticService(prizolov_agent_pb2_grpc.SportsAnalyticServiceServicer):
    """Имитатор сервера Prizolov Agent OS для сбора метрик производительности ИИ"""

    def __init__(self):
        self.packet_count = 0
        self.start_test_time = None
        self.latencies = []

    async def StreamMatchAnalytics(self, request_iterator, context):
        """Принимает высокочастотный поток пакетов ИИ и замеряется сетевой пинг"""
        self.start_test_time = time.time()
        logger.info("[Mock Server] gRPC Стрим успешно открыт. Начался прием пакетов широкой линии...")
        
        try:
            async for package in request_iterator:
                self.packet_count += 1
                current_time_ms = int(time.time() * 1000)
                
                # Расчет сквозной задержки от генерации пакета ИИ до приема сервером
                latency_ms = current_time_ms - package.timestamp_ms
                self.latencies.append(latency_ms)
                
                # Каждые 100 пакетов выводим телеметрию
                if self.packet_count % 100 == 0:
                    avg_latency = sum(self.latencies[-100:]) / 100.0
                    logger.info(
                        f"[Telemetry Update] Получено пакетов: {self.packet_count} | "
                        f"Текущий пинг доставки (Latency): {avg_latency:.2f} мс"
                    )
                    
            # Формируем успешный ответ при закрытии стрима
            return prizolov_agent_pb2.AgentOSStatus(
                is_success=True,
                error_message="",
                processed_timestamp_ms=int(time.time() * 1000)
            )
            
        except Exception as e:
            logger.error(f"[Mock Server Error] Сбой при приеме потока данных: {e}")
            return prizolov_agent_pb2.AgentOSStatus(
                is_success=False,
                error_message=str(e),
                processed_timestamp_ms=int(time.time() * 1000)
            )

async def start_mock_agent_server(port: int = 50051):
    """Запускает асинхронный gRPC Mock Сервер"""
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=5))
    servicer = MockSportsAnalyticService()
    
    prizolov_agent_pb2_grpc.add_SportsAnalyticServiceServicer_to_server(servicer, server)
    server.add_insecure_port(f"[::]:{port}")
    
    logger.info(f"=== Запуск Mock Agent OS gRPC Сервера на порту {port} ===")
    await server.start()
    
    # Мониторим нагрузку в течение 30 секунд, затем выводим итоговый отчет
    await asyncio.sleep(30)
    
    logger.info("=== Стресс-тестирование завершено. Формирование отчета... ===")
    await server.stop(grace=2.0)
    
    if servicer.packet_count > 0:
        duration = time.time() - servicer.start_test_time
        fps_throughput = servicer.packet_count / duration
        max_latency = max(servicer.latencies) if servicer.latencies else 0
        min_latency = min(servicer.latencies) if servicer.latencies else 0
        avg_latency = sum(servicer.latencies) / len(servicer.latencies) if servicer.latencies else 0
        
        print("\n" + "="*50)
        print("    ИТОГОВЫЙ ОТЧЕТ ПРОПУСКНОЙ СПОСОБНОСТИ ИИ-ДВИЖКА")
        print("="*50)
        print(f" Общее время теста:         {duration:.2f} сек")
        print(f" Обработано кадров/линий:   {servicer.packet_count}")
        print(f" Скорость передачи (SPS):   {fps_throughput:.2f} пакетов/сек (Цель: >25 FPS)")
        print(f" Минимальный пинг сети:     {min_latency} мс")
        print(f" Средний пинг сети (Avg):   {avg_latency:.2f} мс (Цель: <10 мс)")
        print(f" Максимальный пинг (Peak):  {max_latency} мс")
        print("="*50 + "\n")
    else:
        logger.warning("Данные от ИИ-движка не поступали. Проверьте настройки AGENT_HOST.")

if __name__ == "__main__":
    try:
        asyncio.run(start_mock_agent_server())
    except KeyboardInterrupt:
        logger.info("Тестирование прервано оператором.")
