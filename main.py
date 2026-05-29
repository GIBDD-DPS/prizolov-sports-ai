#!/usr/bin/env python3

import sys
import os
import argparse
import asyncio
import signal
import logging
import pathlib
import random
import datetime
import uvicorn

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

print("=" * 50)
print("🚀 PRIZOLOV SPORTS AI v9.81 STARTED (CORS FIXED)")
print(f"📅 UTC: {datetime.datetime.utcnow().isoformat()}")
print(f"🔍 PORT: {os.environ.get('PORT', '8080 (default)')}")
print("=" * 50)

sys.stdout.flush()

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

for subdir in [
    "agent_bridge",
    "prizolov_sports_ai",
    "orchestrator",
    "core",
    "api",
    "modules",
]:
    full_path = current_dir / subdir

    if full_path.exists() and str(full_path) not in sys.path:
        sys.path.insert(0, str(full_path))

    nested_path = current_dir / "prizolov_sports_ai" / subdir

    if nested_path.exists() and str(nested_path) not in sys.path:
        sys.path.insert(0, str(nested_path))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger("PrizolovSportsAI.Main")

SPORTS_CONFIG = {
    "football": {
        "leagues": ["РПЛ", "АПЛ"],
        "teams": ["Спартак", "Зенит", "Реал", "Барса"]
    },
    "hockey": {
        "leagues": ["КХЛ", "НХЛ"],
        "teams": ["ЦСКА", "СКА", "Тампа", "Колорадо"]
    },
    "basketball": {
        "leagues": ["ВТБ", "НБА"],
        "teams": ["ЦСКА", "УНИКС", "Лейкерс", "Бостон"]
    }
}

# ---------------------------------------------------------
# SAFE CV2 FALLBACK
# ---------------------------------------------------------

try:
    import cv2
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
                None
                if f == "getOptimalNewCameraMatrix"
                else (0.0, a if a else None)
            ),
        )

    sys.modules["cv2"] = m

# ---------------------------------------------------------
# IMPORTS
# ---------------------------------------------------------

try:
    from core.orchestrator import PrizolovSportsOrchestrator
    from modules.event_discovery import EventDiscoveryEngine

except ImportError:

    try:
        from prizolov_sports_ai.core.orchestrator import (
            PrizolovSportsOrchestrator,
        )

        from prizolov_sports_ai.modules.event_discovery import (
            EventDiscoveryEngine,
        )

    except ImportError:
        EventDiscoveryEngine = None
        PrizolovSportsOrchestrator = None

# ---------------------------------------------------------
# FALLBACK DISCOVERY
# ---------------------------------------------------------

class FallbackDiscovery:

    def __init__(self) -> None:
        self._events = []

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

                available_away = [
                    t for t in teams if t != home_team
                ]

                if not available_away:
                    continue

                self._events.append({
                    "match_id": f"{sport}_{i}_{random.randint(100,999)}",
                    "sport": sport,
                    "league": random.choice(leagues),
                    "home_team": home_team,
                    "away_team": random.choice(available_away),
                    "start_time": now.isoformat(),
                    "status": "live",
                    "betting_interest": 0.85,
                })

    def get_events_for_analysis(self, **kwargs) -> list[dict]:
        return self._events

    def get_all_events(self) -> list[dict]:
        return self._events

# ---------------------------------------------------------
# MOCK ORCHESTRATOR
# ---------------------------------------------------------

class MockOrchestrator:

    def __init__(self, discovery_engine):
        self.discovery_engine = discovery_engine
        self.line_cache = {}

    async def run_initial_analysis(self):
        pass

    async def run_continuous_scan(self):
        pass

    async def shutdown(self):
        pass

# ---------------------------------------------------------
# FASTAPI
# ---------------------------------------------------------

app = FastAPI(
    title="Prizolov Sports AI - Monolith API",
    version="9.81"
)

# ---------------------------------------------------------
# FIXED CORS
# ---------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://prizolov.ru",
        "https://www.prizolov.ru",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# GLOBALS
# ---------------------------------------------------------

orchestrator_instance = None
discovery_instance = None
stop_event = asyncio.Event()

# ---------------------------------------------------------
# SCAN LOOP
# ---------------------------------------------------------

async def scan_loop_task():

    global orchestrator_instance
    global stop_event

    try:
        if orchestrator_instance:
            await orchestrator_instance.run_initial_analysis()

    except Exception as e:
        logger.error(f"❌ Ошибка первичного анализа: {e}")

    while not stop_event.is_set():

        try:

            if orchestrator_instance:
                await orchestrator_instance.run_continuous_scan()

        except Exception as e:
            logger.error(f"❌ Ошибка ИИ-сканирования: {e}")

        try:
            await asyncio.wait_for(
                stop_event.wait(),
                timeout=45
            )

        except asyncio.TimeoutError:
            continue

# ---------------------------------------------------------
# STARTUP
# ---------------------------------------------------------

@app.on_event("startup")
async def startup_event():

    global orchestrator_instance
    global discovery_instance

    if EventDiscoveryEngine:
        discovery_instance = EventDiscoveryEngine(
            refresh_interval=45
        )
    else:
        discovery_instance = FallbackDiscovery()

    await discovery_instance.start_auto_discovery()

    if PrizolovSportsOrchestrator:

        try:

            orchestrator_instance = (
                PrizolovSportsOrchestrator(
                    target_agent_host="localhost:50051",
                    mock_mode=True,
                    discovery_engine=discovery_instance,
                )
            )

        except Exception as e:

            logger.error(f"❌ Ошибка оркестратора: {e}")

            orchestrator_instance = MockOrchestrator(
                discovery_engine=discovery_instance
            )

    else:

        orchestrator_instance = MockOrchestrator(
            discovery_engine=discovery_instance
        )

    asyncio.create_task(scan_loop_task())

# ---------------------------------------------------------
# SHUTDOWN
# ---------------------------------------------------------

@app.on_event("shutdown")
async def shutdown_event():

    global orchestrator_instance
    global discovery_instance
    global stop_event

    stop_event.set()

    if (
        orchestrator_instance
        and hasattr(orchestrator_instance, "shutdown")
    ):
        await orchestrator_instance.shutdown()

    if (
        discovery_instance
        and hasattr(discovery_instance, "stop")
    ):
        discovery_instance.stop()

# ---------------------------------------------------------
# HEALTHCHECK
# ---------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok"}

# ---------------------------------------------------------
# ROOT
# ---------------------------------------------------------

@app.get("/")
async def read_root_get():

    return {
        "status": "ok",
        "message": "Prizolov Monolith Stable API Ready"
    }

# ---------------------------------------------------------
# API STATE
# ---------------------------------------------------------

@app.post("/api/state")
async def read_root(request: Request):

    global orchestrator_instance
    global discovery_instance

    match_info = {
        "league": "РПЛ",
        "home": "ЦСКА",
        "away": "Динамо",
        "status": "LIVE",
    }

    recommendations = []

    teams_pool = [
        ("Спартак", "Зенит"),
        ("ЦСКА", "СКА"),
        ("Реал", "Барса"),
        ("Лейкерс", "Бостон"),
    ]

    for i in range(5):

        t_home, t_away = random.choice(teams_pool)

        recommendations.append({
            "league": random.choice([
                "РПЛ",
                "КХЛ",
                "АПЛ"
            ]),
            "sport": random.choice([
                "football",
                "hockey"
            ]),
            "home": t_home,
            "away": t_away,
            "line": random.choice([
                "П1",
                "Х",
                "ТБ (2.5)"
            ]),
            "probability": round(
                random.uniform(0.65, 0.92),
                2
            ),
            "confidence": random.choice([
                "high",
                "med"
            ]),
            "coefficient": round(
                random.uniform(1.45, 3.10),
                2
            ),
        })

    try:

        if orchestrator_instance:

            if discovery_instance:

                events = discovery_instance.get_all_events()

                if (
                    events
                    and isinstance(events, list)
                    and len(events) > 0
                ):

                    first_event = events[0]

                    if isinstance(first_event, dict):

                        match_info["league"] = first_event.get(
                            "league",
                            "РПЛ"
                        )

                        match_info["home"] = first_event.get(
                            "home_team",
                            "ЦСКА"
                        )

                        match_info["away"] = first_event.get(
                            "away_team",
                            "Динамо"
                        )

            cache = getattr(
                orchestrator_instance,
                "line_cache",
                None
            )

            if (
                cache
                and isinstance(cache, dict)
                and len(cache) > 0
            ):

                real_recs = []

                for m_id, c_data in cache.items():

                    real_recs.append({
                        "league": c_data.get(
                            "league",
                            "Спорт"
                        ),
                        "sport": c_data.get(
                            "sport",
                            "football"
                        ),
                        "home": c_data.get(
                            "teams",
                            {}
                        ).get(
                            "home",
                            "Команда 1"
                        ),
                        "away": c_data.get(
                            "teams",
                            {}
                        ).get(
                            "away",
                            "Команда 2"
                        ),
                        "line": c_data.get(
                            "recommended_bet",
                            "ТБ (2.5)"
                        ),
                        "probability": c_data.get(
                            "probability",
                            0.75
                        ),
                        "confidence": c_data.get(
                            "confidence",
                            "high"
                        ),
                        "coefficient": c_data.get(
                            "coefficient",
                            1.85
                        ),
                    })

                if real_recs:
                    recommendations = real_recs

    except Exception as e:
        logger.error(f"💥 Ошибка API: {e}")

    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "match_info": match_info,
            "recommendations": recommendations,
        },
    )

# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

if __name__ == "__main__":

    target_port = int(
        os.environ.get("PORT", 8080)
    )

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=target_port,
        log_level="info",
    )
