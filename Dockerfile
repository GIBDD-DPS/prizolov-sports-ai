# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.18 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir \
        --index-url https://pypi.org/simple \
        -r requirements.txt

COPY backend/alembic.ini .
COPY backend/alembic ./alembic
COPY backend/app ./app
COPY backend/static ./static

ENV PYTHONUNBUFFERED=1
EXPOSE 8080

CMD ["sh", "-c", "echo '=== PRIZOLOV DOCKER START v14.18 ===' && alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8080"]
