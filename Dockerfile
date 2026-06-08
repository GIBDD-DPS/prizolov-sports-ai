# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.24 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================
# VERIFY in Amvera build logs: "PRIZOLOV DOCKERFILE v14.24" and EXPOSE 8080
# WRONG build shows: appuser, EXPOSE 8000, COPY . .

FROM python:3.11-slim

RUN echo "=== PRIZOLOV DOCKERFILE v14.24 (port 8080, no appuser) ==="

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

CMD ["sh", "-c", "echo '=== PRIZOLOV DOCKER START v14.24 ===' && alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8080"]
