from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import os
from datetime import datetime

# Импортируем вашу логику состояний
try:
    from orchestrator.live_match_state import LiveMatchState
except ImportError:
    # Защита на случай изменения структуры папок
    from prizolov_sports_ai.orchestrator.live_match_state import LiveMatchState

app = FastAPI(
    title="Prizolov Sports AI - Public API",
    version="1.10",
    description="Public JSON API for prizolov.ru sports widgets (WordPress / Elementor)."
)

# Идеальная CORS-настройка для WordPress / Elementor
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Моковый реестр на случай, если оркестратор еще не передал живые матчи
_fallback_registry = {
    "rpl_cska_dinamo_2026": LiveMatchState("rpl_cska_dinamo_2026")
}

@app.get("/")
def read_root():
    """Эндпоинт для проверки здоровья (Healthcheck) в Amvera Cloud."""
    return {
        "status": "ok",
        "service": "Prizolov Sports AI FastAPI",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/match/live/{match_id}")
def get_live_match_state(match_id: str, request: Request):
    # Пытаемся получить живой оркестратор из состояния приложения
    orch = app.state.orchestrator if hasattr(app.state, "orchestrator") else None
    
    # Если в оркестраторе есть кэш линий/матчей, ищем там
    if orch and hasattr(orch, "line_cache") and match_id in orch.line_cache:
        return orch.line_cache[match_id]
        
    # Если в оркестраторе нет, ищем в резервном реестре LiveMatchState
    if match_id in _fallback_registry:
        return _fallback_registry[match_id].build_state()
        
    raise HTTPException(status_code=404, detail="Match not found or not analyzed yet")
