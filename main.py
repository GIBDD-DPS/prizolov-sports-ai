```python
# ============================================
# Prizolov Sports AI Backend
# Version: 1.03
# Author: Dm.Andreyanov
# ============================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ============================================
# FASTAPI INIT
# ============================================

app = FastAPI(
    title="Prizolov Sports AI",
    version="1.03"
)

# ============================================
# CORS FIX
# ============================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://prizolov.ru",
        "https://www.prizolov.ru",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# ROOT ROUTE
# ============================================

@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "Prizolov Sports AI"
    }

# ============================================
# API STATE
# ============================================

@app.post("/api/state")
async def state():

    return {
        "match_info": {
            "league": "Premier League",
            "home": "Manchester City",
            "away": "Arsenal",
            "status": "LIVE"
        },

        "recommendations": [
            {
                "league": "Premier League",
                "sport": "football",
                "home": "Manchester City",
                "away": "Arsenal",
                "line": "ТБ 2.5",
                "probability": 0.74,
                "confidence": "high",
                "coefficient": 1.92
            },
            {
                "league": "La Liga",
                "sport": "football",
                "home": "Barcelona",
                "away": "Real Madrid",
                "line": "П1",
                "probability": 0.67,
                "confidence": "medium",
                "coefficient": 2.15
            }
        ]
    }

# ============================================
# PREFLIGHT OPTIONS FIX
# ============================================

@app.options("/{rest_of_path:path}")
async def preflight_handler(rest_of_path: str):

    response = JSONResponse(content={})

    response.headers["Access-Control-Allow-Origin"] = "https://prizolov.ru"
    response.headers["Access-Control-Allow-Methods"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"

    return response

# ============================================
# HEALTHCHECK
# ============================================

@app.get("/health")
async def health():
    return {
        "status": "healthy"
    }
```
