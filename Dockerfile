# ============================================
# Prizolov Sports AI - Production Dockerfile
# Version: 5.02 (Headless OS Patch)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Optimized Multi-Stage Container Build with OpenCV Fix
# ============================================

# Шаг 1: Сборка и подготовка зависимостей
FROM python:3.10-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Устанавливаем зависимости в изолированную директорию пользователя
RUN pip install --no-cache-dir --user -r requirements.txt

# Шаг 2: Финальный легковесный образ для исполнения
FROM python:3.10-slim AS runner

WORKDIR /app

# Исправлено: Добавлен принудительный апдейт и установка графических библиотек OpenGL/Mesa 
# для полной ликвидации ошибки ImportError: libGL.so.1 в Amvera Cloud
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgl1-mesa-glx \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Копируем установленные пакеты из предыдущего шага сборщика
COPY --from=builder /root/.local /root/.local
COPY . .

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

# Создаем папку постоянных данных для кэша и логов аудита
RUN mkdir -p /data

EXPOSE 8080

CMD ["python", "main.py", "--sport", "football", "--match_id", "prod_match_001", "--agent_host", "agent-os:50051"]
