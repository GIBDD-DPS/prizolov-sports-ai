# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.24 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================
# VERIFY in Amvera build logs: "PRIZOLOV DOCKERFILE v14.24" and EXPOSE 8080
# WRONG build shows: appuser, EXPOSE 8000, COPY . .

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем ВСЁ приложение (включая папку app, если она нужна)
COPY . .

# Непривилегированный пользователь
RUN useradd -m prizolov && chown -R prizolov:prizolov /app
USER prizolov

EXPOSE 8000

# Точка входа — корневой main.py
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
