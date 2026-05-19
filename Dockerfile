# ============================================
# Prizolov Sports AI - Headless OS Container
# Version: 6.05 (+1.01: Production Environment Flexibility & Mock Mode Support)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production Headless Multi-Object Tracking Environment
# ============================================

FROM python:3.10-slim

WORKDIR /app

# Обновление и установка базовых библиотек ОС для OpenCV и сетевых операций
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgl1 \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Установка Python пакетов без кэша
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Переменные окружения с безопасными дефолтами для гибкого деплоя
ENV PYTHONUNBUFFERED=1 \
    QT_QPA_PLATFORM=offscreen \
    SPORT=football \
    MATCH_ID=prod_match_001 \
    AGENT_HOST=localhost:50051 \
    DASHBOARD_PORT=8080 \
    MOCK_MODE=false

EXPOSE 8080

# Используем shell-форму CMD для поддержки подстановки переменных окружения
# При MOCK_MODE=true автоматически добавляется флаг --mock-mode
CMD sh -c "python main.py \
    --sport $SPORT \
    --match_id $MATCH_ID \
    --agent_host $AGENT_HOST \
    --dashboard_port $DASHBOARD_PORT \
    $([ \"$MOCK_MODE\" = \"true\" ] && echo \"--mock-mode\")"
