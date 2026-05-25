#!/usr/bin/env python3
# ============================================
# Prizolov Sports AI - Main Execution Engine
# Version: 8.56 (+0.01: Multi-sport constants, safer fallback discovery, minor cleanup)
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

# === ЖЁСТКИЙ БАННЕР ВЕРСИИ ===
print("=" * 50)
print("🚀 PRIZOLOV SPORTS AI v8.56 STARTED (HTTP MODE)")
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
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / "agent_bridge"))
sys.path.insert(0, str(current_dir / "prizolov_sports_ai"))

# === БАЗОВАЯ КОНФИГУРАЦИЯ СПОРТОВ ===
# Основные виды спорта: футбол, хоккей, баскетбол.
# "other" зарезервирован под интересные события в других видах спорта.
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
    # "other": можно будет использовать для дополнительных видов спорта
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
        logging.warning(f"⚠️ Proto skipped: {e}")


compile_proto()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("PrizolovSportsAI.Main")

keep_running = True
signal.signal(
    signal.SIGINT, lambda s, f: setattr(__import__("__main__"), "keep_running", False)
)
signal.signal(
    signal.SIGTERM, lambda s, f: setattr(__import__("__main__"), "keep_running", False)
)

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


# === FALLBACK DISCOVERY ===
class FallbackDiscovery:
    """
    Резервный механизм обнаружения событий,
    когда EventDiscoveryEngine недоступен.
    Использует SPORTS_CONFIG и генерирует
    базовый набор матчей по основным видам спорта.
    """

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
                # гарантируем, что away_team != home_team
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

        logger.info(
            f"🧪 FallbackDiscovery generated {len(self._events)} events "
            f"for sports: {', '.join(SPORTS_CONFIG.keys())}"
        )

    def get_events_for_analysis(self, **kwargs) -> list[dict]:
        return self._events

    def get_all_events(self) -> list[dict]:
        return self._events


async def main_loop(host: str, port: int, mock: bool) -> None:
    global keep_running
    logger.info("🔄 Инициализация пайплайна v8.56...")
    logger.info(
        f"🎯 Target agent host: {host} | HTTP port: {port} | MOCK_MODE: {'ON' if mock else 'OFF'}"
    )

    # Discovery engine: реальный или fallback
    disc = EventDiscoveryEngine(refresh_interval=45) if EventDiscoveryEngine else FallbackDiscovery()
    await disc.start_auto_discovery()
    logger.info(f"✅ Discovery ready. Events: {len(disc.get_all_events())}")

    orch = PrizolovSportsOrchestrator(
        target_agent_host=host,
        mock_mode=mock,
        discovery_engine=disc,
    )

    await start_api_server(orch, port=port)
    logger.info("✅ HTTP API Server active")

    # Первичный анализ (может быть расширен под многоспорт и самообучение)
    await orch.run_initial_analysis()

    try:
        while keep_running:
            await orch.run_continuous_scan()
            await asyncio.sleep(45)
    finally:
        await orch.shutdown()
        logger.info("🛑 Orchestrator shutdown complete")


if __name__ == "__main__":
    # Amvera передаёт порт через переменную окружения PORT
    default_port = int(os.environ.get("PORT", 8080))

    parser = argparse.ArgumentParser()
    parser.add_argument("--agent_host", default="localhost:50051")
    parser.add_argument("--dashboard_port", type=int, default=default_port)
    parser.add_argument("--mock-mode", action="store_true")
    parser.add_argument("--sport", type=str, default=None, help="[DEPRECATED]")
    parser.add_argument("--match_id", type=str, default=None, help="[DEPRECATED]")
    parser.add_argument("--weights", type=str, default=None, help="[DEPRECATED]")

    args, unknown = parser.parse_known_args()

    if args.sport or args.match_id:
        logger.warning("⚠️ Deprecated args ignored. Using autonomous discovery.")

    try:
        asyncio.run(main_loop(args.agent_host, args.dashboard_port, args.mock_mode))
    except KeyboardInterrupt:
        logger.info("👋 Shutdown.")
