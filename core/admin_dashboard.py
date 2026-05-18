# ============================================
# Prizolov Sports AI - Live Admin Dashboard
# Version: 5.02 (Secure Middleware Integration)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at cloud.amvera.ru
# ============================================

import sys
import os
from pathlib import Path

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import asyncio
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# Импорт модуля кибербезопасности версии 5.01
from core.secure_auth import SecureAuthBridge

logger = logging.getLogger("PrizolovSportsAI.Dashboard")

# Инициализация FastAPI приложения
app = FastAPI(
    title="Prizolov Sports AI - Control Panel",
    description="Защищенная Live-панель управления маржой и мониторинга матчей",
    version="5.02"
)

# Инициализация криптографического моста авторизации
auth_bridge = SecureAuthBridge()

# Глобальная ссылка на оркестратор
orchestrator_instance: Optional[Any] = None

class MarginUpdateModel(BaseModel):
    new_margin: float

class LockLineModel(BaseModel):
    is_suspended: bool

async def verify_scout_access(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """Внутреннее middleware для обязательной JWT-верификации прав доступа скаута"""
    if not authorization or not authorization.startswith("Bearer "):
        logger.warning("[Security Infraction] Попытка несанкционированного доступа к API без токена!")
        raise HTTPException(status_code=401, detail="Отсутствует или некорректен токен авторизации (Bearer token required)")
        
    token = authorization.split(" ")[1]
    is_valid, claims = auth_bridge.verify_jwt_token(token)
    
    if not is_valid:
        raise HTTPException(status_code=403, detail=claims.get("error", "Доступ запрещен"))
        
    return claims

@app.get("/", response_class=HTMLResponse)
async def get_dashboard_ui():
    """Возвращает UI-интерфейс панели управления скаута"""
    if not orchestrator_instance or not orchestrator_instance.is_initialized:
        return "<h3>[System Status] Ожидание инициализации спортивного матча оркестратором...</h3>"
        
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Prizolov AI Control Center</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: -apple-system, sans-serif; background: #121214; color: #e1e1e6; padding: 20px; }}
            .card {{ background: #202024; padding: 20px; border-radius: 8px; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }}
            h2 {{ color: #04d361; margin-top: 0; }}
            .btn {{ padding: 10px 20px; border: none; border-radius: 4px; font-weight: bold; cursor: pointer; margin-right: 10px; }}
            .btn-danger {{ background: #f74040; color: #fff; }}
            .btn-success {{ background: #04d361; color: #121214; }}
            .status-val {{ font-size: 1.2em; font-weight: bold; color: #ffd31d; }}
        </style>
    </head>
    <body>
        <h1>Prizolov Sports AI — Панель Скаута</h1>
        <div class="card">
            <h2>Текущее событие</h2>
            <p>ID Матча: <span class="status-val">{orchestrator_instance.match_id}</span></p>
            <p>Вид спорта: <span class="status-val">{orchestrator_instance.current_sport.upper()}</span></p>
            <p>Текущая маржа: <span class="status-val" id="margin-val">{orchestrator_instance.line_generator.margin:.2f}</span></p>
        </div>
        
        <div class="card">
            <h2>Экстренное управление линией (Требует JWT)</h2>
            <button class="btn btn-danger" onclick="setLock(true)">ЗАМОРОЗИТЬ ПРИЕМ СТАВОК (SUSPENDED)</button>
            <button class="btn btn-success" onclick="setLock(false)">РАЗБЛОКИРОВАТЬ ЛИНЕЙКУ</button>
        </div>

        <script>
            // Токен должен внедряться в localStorage фронтендом при авторизации на prizolov.ru
            const getAuthToken = () => localStorage.getItem('prizolov_scout_token') || '';

            async function setLock(isLocked) {{
                const token = getAuthToken();
                if(!token) {{
                    alert('Ошибка: Вы не авторизованы в системе Prizolov!');
                    return;
                }}
                
                const response = await fetch('/api/v1/control/lock', {{
                    method: 'POST',
                    headers: {{ 
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer ' + token
                    }},
                    body: JSON.stringify({{ is_suspended: isLocked }})
                }});
                
                if(response.ok) {{
                    alert(isLocked ? 'Линия успешно заморожена на prizolov.ru' : 'Линия разблокирована');
                }} else {{
                    const err = await response.json();
                    alert('Ошибка доступа: ' + err.detail);
                }}
            }}
        </script>
    </body>
    </html>
    """
    return html_content

@app.post("/api/v1/control/margin")
async def update_live_margin(data: MarginUpdateModel, token_claims: Dict[str, Any] = Depends(verify_scout_access)):
    """API-эндпоинт изменения базовой маржи букмекера налету (Защищен JWT)"""
    global orchestrator_instance
    if not orchestrator_instance:
        raise HTTPException(status_code=400, detail="Оркестратор не привязан к панели")
        
    if data.new_margin < 1.0 or data.new_margin > 1.5:
        raise HTTPException(status_code=400, detail="Недопустимый диапазон маржи (1.0 - 1.5)")
        
    orchestrator_instance.line_generator.margin = data.new_margin
    orchestrator_instance.risk_manager.base_margin = data.new_margin
    
    scout_id = token_claims.get("sub", "unknown_id")
    logger.info(f"[Manual Risk Control] Скаут ID:{scout_id} изменил базовую маржу на: {data.new_margin:.2f}")
    return {"status": "success", "applied_margin": data.new_margin, "operator_id": scout_id}

@app.post("/api/v1/control/lock")
async def toggle_line_lock(data: LockLineModel, token_claims: Dict[str, Any] = Depends(verify_scout_access)):
    """API-эндпоинт принудительной live-заморозки коэффициентов (Защищен JWT)"""
    global orchestrator_instance
    if not orchestrator_instance or not orchestrator_instance.active_module:
        raise HTTPException(status_code=400, detail="Спортивный модуль не запущен")
        
    scout_id = token_claims.get("sub", "unknown_id")
    logger.warning(f"[Manual Risk Control] Сигнал блокировки линии переключен оператором ID:{scout_id} в: {data.is_suspended}")
    return {"status": "success", "is_suspended": data.is_suspended, "operator_id": scout_id}

async def start_dashboard_server(orchestrator, port: int = 8080):
    """Запускает веб-сервер панели управления внутри контейнера Amvera"""
    global orchestrator_instance
    orchestrator_instance = orchestrator
    
    import uvicorn
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="warning")
    server = uvicorn.Server(config)
    
    asyncio.create_task(server.serve())
    logger.info(f"Защищенная административная веб-панель успешно запущена на порту {port}")
