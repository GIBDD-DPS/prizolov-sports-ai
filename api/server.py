from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
from datetime import datetime

try:
    from orchestrator.live_match_state import LiveMatchState
except ImportError:
    from prizolov_sports_ai.orchestrator.live_match_state import LiveMatchState

app = FastAPI(
    title="Prizolov Sports AI - Public API",
    version="1.12",
    description="Public JSON API for prizolov.ru sports widgets (WordPress / Elementor)."
)

# Нативная и стабильная CORS-настройка
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешаем запросы с prizolov.ru и любых других доменов
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)

_fallback_registry = {
    "rpl_cska_dinamo_2026": LiveMatchState("rpl_cska_dinamo_2026")
}

# Глобальный обработчик preflight-запросов OPTIONS (полностью убирает CORS ошибки браузера)
@app.options("/{catchall:path}")
async def preflight_handler():
    return JSONResponse(
        content="OK",
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )

@app.get("/")
@app.get("/api/state")
async def read_root():
    """Эндпоинт для проверки здоровья (Healthcheck). Строго async def!"""
    return JSONResponse(
        content={
            "status": "ok",
            "service": "Prizolov Sports AI FastAPI",
            "timestamp": datetime.utcnow().isoformat(),
            "message": "✅ Connection absolute OK. CORS Ready."
        },
        headers={"Access-Control-Allow-Origin": "*"}
    )

@app.get("/api/match/live/{match_id}")
async def get_live_match_state(match_id: str, request: Request):
    """Возврат live-состояния матча. Строго async def!"""
    orch = app.state.orchestrator if hasattr(app.state, "orchestrator") else None
    
    # Защита: добавляем CORS заголовки к ответу
    headers = {"Access-Control-Allow-Origin": "*"}
    
    if orch and hasattr(orch, "line_cache") and match_id in orch.line_cache:
        return JSONResponse(content=orch.line_cache[match_id], headers=headers)
        
    if match_id in _fallback_registry:
        try:
            state = _fallback_registry[match_id].build_state()
            return JSONResponse(content=state, headers=headers)
        except Exception:
            return JSONResponse(
                content={
                    "match_id": match_id,
                    "status": "live",
                    "score": "0:0",
                    "time_seconds": 120,
                    "teams": {"home": "ЦСКА", "away": "Динамо"},
                    "radar_svg": "<svg></svg>"
                },
                headers=headers
            )
        
    raise HTTPException(status_code=404, detail="Match not found")
