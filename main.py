import os
import logging
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("prizolov-ai")

# ОБЯЗАТЕЛЬНО перед использованием декораторов
app = FastAPI(title="Prizolov Sports AI")

@app.on_event("startup")
async def startup_event():
    logger.info("=== Сервис прогнозов запущен ===")

@app.get("/api/v1/storefront-widget", response_class=HTMLResponse)
async def storefront_widget():
    """Виджет прогноза для WordPress."""
    try:
        # --- Вставьте сюда ваш реальный код прогноза ---
        # from app.predictor import get_prediction
        # prediction = get_prediction()
        # return HTMLResponse(content=f"<div>Победитель: {prediction['winner']} ({prediction['probability']}%)</div>")
        return HTMLResponse(content="<h3>⚽ Прогноз готов</h3>")
    except Exception as e:
        logger.error(f"Ошибка виджета: {e}")
        return HTMLResponse(content="<div class='error'>Сервис временно недоступен</div>", status_code=500)

@app.get("/health")
async def health():
    return {"status": "ok"}
