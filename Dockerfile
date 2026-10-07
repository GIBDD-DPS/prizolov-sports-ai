# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.42 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# git нужен, чтобы pip мог поставить зависимость agenomics по git-ссылке
# (agenomics @ git+https://github.com/GIBDD-DPS/agenomics.git в requirements.txt).
# python:3.11-slim не содержит git по умолчанию — без этого шага сборка падает
# с "ERROR: Cannot find command 'git'".
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем всё приложение
COPY . .

# Пользователь без root
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

# Приложение импортирует себя как пакет app (from app.core.config ...), а
# статику ищет в ./static относительно текущего каталога: обе вещи лежат в
# backend/, поэтому запуск идёт из backend/ как app.main:app. Запуск из
# корня как backend.app.main:app падал с ModuleNotFoundError: No module named 'app'.
WORKDIR /app/backend
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
