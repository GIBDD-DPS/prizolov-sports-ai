# ============================================
# Prizolov Sports AI - Public API Gateway
# Version: 1.10 (Orchestrator Integration)
#
# CHANGELOG:
# 1.10:
# - Удалён mock-слой
# - Подключён реальный orchestrator LiveMatchState
# - Создан глобальный MatchRegistry для хранения live-состояний
# - Endpoint /api/match/live/{match_id} теперь отдаёт реальные данные
# - Полная совместимость с WordPress / Elementor
#
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Public integration with prizolov.ru (WordPress / Elementor)
# ============================================

import sys
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from orchestrator.live_match_state import LiveMatchState


# ============================================================
# ИНИЦИАЛИЗАЦИЯ API
# ============================================================

app = FastAPI(
    title="Prizolov Sports AI - Public API",
    version="1.10",
    description="Public JSON API for prizolov.ru sports widgets (WordPress / Elementor)."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # в проде заменить на https://prizolov.ru
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# РЕЕСТР АКТИВНЫХ МАТЧЕЙ
# ============================================================

class MatchRegistry:
    """
    Хранилище live-состояний всех активных матчей.
    В продакшене может быть Redis / PostgreSQL / Kafka.
    Пока — in-memory.
    """

    def __init__(self):
        self.matches: Dict[str, LiveMatchState] = {}

    def get(self, match_id: str) -> LiveMatchState:
        if match_id not in self.matches:
            raise KeyError(f"Match '{match_id}' not found in registry")
        return self.matches[match_id]

    def create(self, match_id: str) -> LiveMatchState:
        state = LiveMatchState(match_id)
        self.matches[match_id] = state
        return state


registry = MatchRegistry()

# Создаём live-инстанс матча ЦСКА–Динамо
registry.create("rpl_cska_dinamo_2026")


# ============================================================
# PUBLIC ENDPOINT
# ============================================================

@app.get("/api/match/live/{match_id}")
def get_live_match_state(match_id: str) -> Dict[str, Any]:
    """
    Расширенный live-endpoint для интеграции с WordPress / Elementor.
    Возвращает полный live-state матча.
    """
    try:
        match_state = registry.get(match_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Match not found")

    return match_state.build_state()
