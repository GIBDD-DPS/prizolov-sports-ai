# ============================================
# Copyright (c) 2026
# Prizolov Agent OS v3.023
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Prizolov Sports AI", version="3.023")

# Максимально широкий CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Prizolov Sports AI API"}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/api/state")
async def get_state():
    # Временно простой ответ, без внешних API
    return {
        "match_info": {
            "league": "Тестовая лига",
            "home": "Команда А",
            "away": "Команда Б",
            "status": "LIVE"
        },
        "recommendations": [
            {
                "league": "Тест",
                "sport": "football",
                "home": "Команда А",
                "away": "Команда Б",
                "line": "Тотал больше 2.5",
                "confidence": "high",
                "probability": 0.75,
                "coefficient": 1.90
            }
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
