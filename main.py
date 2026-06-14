import os
import logging
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

# Импорт из файлов в той же директории
from predictor import get_prediction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("prizolov-ai")

app = FastAPI(title="Prizolov Sports AI")

@app.on_event("startup")
async def startup_event():
    logger.info("=== Сервис прогнозов запущен ===")

@app.get("/api/v1/storefront-widget", response_class=HTMLResponse)
async def storefront_widget():
    try:
        prediction = get_prediction()
        if "error" in prediction:
            return HTMLResponse(
                content=f"<div class='ai-error'>Ошибка: {prediction['error']}</div>"
            )
        html = f"""
        <div class="ai-prediction">
            <h3>🏆 Прогноз AI</h3>
            <p>Победитель: <strong>{prediction['winner']}</strong></p>
            <p>Вероятность: {prediction['probability']}%</p>
        </div>
        """
        return HTMLResponse(content=html)
    except Exception as e:
        logger.exception("Критическая ошибка")
        return HTMLResponse(
            content="<div class='ai-error'>Сервис временно недоступен</div>",
            status_code=500
        )

@app.get("/health")
async def health():
    return {"status": "ok"}
