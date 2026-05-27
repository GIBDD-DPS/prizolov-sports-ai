#!/usr/bin/env python3
# ============================================
# Prizolov Sports AI - Main Execution Engine
# Version: 8.57 (PRODUCTION OPTIMIZED FOR AMVERA)
# Author: Dm.Andreyanov / Refactored
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

# === ЖЁСТКИЙ БАННЕР ВЕРСИИ ===
print("=" * 50)
print("🚀 PRIZOLOV SPORTS AI v8.57 STARTED (HTTP MODE)")
print(f"📅 UTC: {datetime.datetime.utcnow().isoformat()}")
print(f"🔍 PORT: {os.environ.get('PORT', '8080 (default)')}")
print("=" * 50)
sys.stdout.flush()

# Инжекция типов
import builtins
import typing

for a, v in [
    ("Path", pathlib.Path),
    ("Tuple", typing.Tuple),
    ("List", typing.List),
    ("Dict", typing.Dict),
    ("Any", typing.Any),
    ("Optional", typing.Optional),
]:
    setattr(builtins, a, v)

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["OPENCV_LOG_LEVEL"] = "ERROR"

current_dir = pathlib.Path(__file__).resolve().parent
for path_dir in [current_dir, current_dir / "agent_bridge", current_dir / "prizolov_sports_ai"]:
    if str(path_dir) not in sys.path:
        sys.path.insert(0, str(path_dir))

# === БАЗОВАЯ КОНФИГУРАЦИЯ СПОРТОВ ===
SPORTS_CONFIG = {
    "football": {
        "leagues": ["РПЛ", "АПЛ"],
        "teams": ["Спартак", "Зенит", "Реал", "Барса"],
    },
    "hockey": {
        "leagues": ["КХЛ", "НХЛ"],
        "teams": ["ЦСКА", "СКА", "Тампа", "Колорадо"],
    },
    "basketball": {
        "leagues": ["ВТБ", "НБА"],
        "teams": ["ЦСКА", "УНИКС", "Лейкерс", "Бостон"],
    },
}

# CV Mock
try:
    import cv2  # type: ignore
except Exception:
    from types import ModuleType

    m = ModuleType("cv2")
    for x in [
        "COLOR_BGR2GRAY",
        "COLOR_BGR2YCrCb",
        "COLOR_YCrCb2BGR",
        "INTER_CUBIC",
        "INTER_NEAREST",
        "THRESH_BINARY_INV",
        "THRESH_OTSU",
        "IMWRITE_JPEG_QUALITY",
        "INPAINT_NS",
    ]:
        setattr(m, x, 0)
    for f in [
        "VideoCapture",
        "resize",
        "cvtColor",
        "threshold",
        "inRange",
        "line",
        "putText",
        "imwrite",
        "undistortPoints",
        "undistort",
        "getOptimalNewCameraMatrix",
    ]:
        setattr(
            m,
            f,
            lambda *a, **k: (
                None if f == "getOptimalNewCameraMatrix" else (0.0, a[0] if a else None)
            ),
        )
    sys.modules["cv2"] = m


def compile_proto() -> None:
    try:
        from grpc_tools import protoc

        p = current_dir / "proto" / "prizolov_agent.proto"
        o = current_dir / "agent_bridge"
        if p.exists():
            o.mkdir(parents=True, exist_ok=True)
            protoc.main(
                [
                    "grpc_tools.protoc",
                    f"--proto_path={p.parent}",
                    f"--python_out={o}",
                    f"--grpc_python_out={o}",
                    str(p),
                ]
            )
            g = o / "prizolov_agent_pb2_grpc.py"
            if g.exists():
                g.write_text(
                    g.read_text(encoding="utf-8").replace(
                        "from . import prizolov_agent_pb2", "import prizolov_agent_pb2"
                    ),
                    encoding="utf-8",
                )
    except Exception as e:
        print(f"⚠️ Proto skipped: {e}")


compile_proto()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("PrizolovSportsAI.Main")

# === ИМПОРТЫ С FALLBACK ===
try:
    from core.orchestrator import PrizolovSportsOrchestrator
    from core.admin_dashboard import start_api_server
    from modules.event_discovery import EventDiscoveryEngine
except ImportError:
    try:
        from prizolov_sports_ai.core.orchestrator import PrizolovSportsOrchestrator
        from prizolov_sports_ai.core.admin_dashboard import start_api_server
        from prizolov_sports_ai.modules.event_discovery import EventDiscoveryEngine
    except ImportError:
        EventDiscoveryEngine = None  # type: ignore
        PrizolovSportsOrchestrator = None  # type: ignore
        start_api_server = None  # type: ignore


class FallbackDiscovery:
    def __init__(self) -> None:
        self._events: list[dict] = []

    async def start_auto_discovery(self) -> None:
        await self._fetch()

    def stop(self) -> None:
        pass

    async def _fetch(self) -> None:
        now = datetime.datetime.utcnow()
        self._events = []

        for sport, cfg in SPORTS_CONFIG.items():
            leagues = cfg.get("leagues", [])
            teams = cfg.get("teams", [])
            if not leagues or len(teams) < 2:
                continue

            for i in range(2):
                home_team = random.choice(teams)
                available_away = [t for t in teams if t != home_team]
                if not available_away:
                    continue
                away_team = random.choice(available_away)

                self._events.append(
                    {
                        "match_id": f"{sport}_{i}_{random.randint(100, 999)}",
                        "sport": sport,
                        "league": random.choice(leagues),
                        "home_team": home_team,
                        "away_team": away_team,
                        "start_time": now.isoformat(),
                        "status": "live",
                        "betting_interest": 0.85,
                    }
                )

        logger.info(f"🧪 FallbackDiscovery generated {len(self._events)} events.")

    def get_events_for_analysis(self, **kwargs) -> list[dict]:
        return self._events

    def get_all_events(self) -> list[dict]:
        return self._events


async def scan_loop(orch, stop_event: asyncio.Event) -> None:
    """Фоновый конкурентный цикл сканирования матчей."""
    logger.info("⚡ Выполнение первичного анализа оркестратора...")
    try:
        await orch.run_initial_analysis()
    except Exception as e:
        logger.error(f"❌ Ошибка первичного анализа: {e}")

    logger.info("🔄 Пайплайн сканирования активирован.")
    while not stop_event.is_set():
        try:
            await orch.run_continuous_scan()
        except Exception as e:
            logger.error(f"❌ Ошибка при непрерывном сканировании: {e}")
        
        try:
            # Безопасный сон с возможностью мгновенного прерывания по сигналу Amvera
            await asyncio.wait_for(stop_event.wait(), timeout=45)
        except asyncio.TimeoutError:
            continue


async def main_loop(host: str, port: int, mock: bool) -> None:
    logger.info("🔄 Инициализация пайплайна v8.57...")
    
    if PrizolovSportsOrchestrator is None or start_api_server is None:
        logger.critical("❌ Критические модули проекта не импортированы. Проверьте структуру папок core/ и модулей.")
        return

    disc = EventDiscoveryEngine(refresh_interval=45) if EventDiscoveryEngine else FallbackDiscovery()
    await disc.start_auto_discovery()
    logger.info(f"✅ Discovery ready. Событий найдено: {len(disc.get_all_events())}")

    orch = PrizolovSportsOrchestrator(
        target_agent_host=host,
        mock_mode=mock,
        discovery_engine=disc,
    )

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    # Чистый перехват системных сигналов выключения контейнера
    def handle_exit():
        logger.info("🛑 Получен сигнал остановки (SIGINT/SIGTERM). Завершаем процессы...")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, handle_exit)
        except NotImplementedError:
            pass # Для тестов локально на Windows, если применимо

    try:
        # Запуск API сервера и фонового сканирования одновременно (конкурентно)
        await asyncio.gather(
            start_api_server(orch, port=port),
            scan_loop(orch, stop_event)
        )
    except Exception as e:
        logger.error(f"❌ Критический сбой в основном цикле asyncio: {e}")
    finally:
        await orch.shutdown()
        if hasattr(disc, 'stop'):
            disc.stop()
        logger.info("🛑 Оркестратор успешно остановлен.")


if __name__ == "__main__":
    # Чтение порта из окружения (Amvera прокидывает его автоматически)
    default_port = int(os.environ.get("PORT", 8080))

    parser = argparse.ArgumentParser(description="Prizolov Sports AI Engine")
    parser.add_argument("--agent_host", default="localhost:50051")
    parser.add_argument("--dashboard_port", type=int, default=default_port)
    parser.add_argument("--mock-mode", action="store_true", default=True) # default=True для безопасных тестов
    parser.add_argument("--sport", type=str, default=None, help="[DEPRECATED]")

    args = parser.parse_args()

    try:
        asyncio.run(main_loop(
            host=args.agent_host,
            port=args.dashboard_port,
            mock=args.mock_mode
        ))
    except KeyboardInterrupt:
        print("🤖 Приложение остановлено пользователем.")
