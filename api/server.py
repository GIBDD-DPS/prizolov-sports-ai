from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
from datetime import datetime

# Импортируем вашу логику состояний
try:
    from orchestrator.live_match_state import LiveMatchState
except ImportError:
    from prizolov_sports_ai.orchestrator.live_match_state import LiveMatchState

app = FastAPI(
    title="Prizolov Sports AI - Public API",
    version="1.11",
    description="Public JSON API for prizolov.ru sports widgets (WordPress / Elementor)."
)

# === МАКСИМАЛЬНО ДОЛОВЕРИЕ CORS ДЛЯ WORDPRESS ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешает запросы с любых доменов, включая prizolov.ru
    allow_credentials=False,  # Важно: должно быть False, если используется ["*"]
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Моковый реестр на случай, если оркестратор еще не передал живые матчи
_fallback_registry = {
    "rpl_cska_dinamo_2026": LiveMatchState("rpl_cska_dinamo_2026")
}

# Кастомный Middleware для принудительного добавления заголовков в обход сбоев FastAPI
@app.middleware("http")
async def add_custom_cors_headers(request: Request, call_next):
    if request.method == "OPTIONS":
        response = JSONResponse(content="OK", status_code=204)
    else:
        response = await call_next(request)
        
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response


@app.get("/")
@app.get("/api/state")
def read_root():
    """Эндпоинт для проверки здоровья (Healthcheck) в Amvera Cloud."""
    return {
        "status": "ok",
        "service": "Prizolov Sports AI FastAPI",
        "timestamp": datetime.utcnow().isoformat(),
        "message": "✅ Connection absolute OK. CORS Ready."
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
        try:
            return _fallback_registry[match_id].build_state()
        except Exception:
            # Если метод .build_state() выдает ошибку, возвращаем базовый JSON, чтобы фронт не падал
            return {
                "match_id": match_id,
                "status": "live",
                "score": "0:0",
                "time_seconds": 120,
                "teams": {"home": "ЦСКА", "away": "Динамо"},
                "radar_svg": "<svg></svg>"
            }
        
    raise HTTPException(status_code=404, detail="Match not found")
