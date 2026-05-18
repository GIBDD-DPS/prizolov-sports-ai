# ============================================
# Prizolov Sports AI - Headless OS Container
# Version: 5.03 (Strict Core OS Patch)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production Headless Multi-Object Tracking Environment
# ============================================

FROM python:3.10-slim

WORKDIR /app

# Принудительное обновление менеджера пакетов Debian и установка системных 
# графических драйверов OpenGL/Mesa для ультимативного устранения падения cv2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgl1 \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Установка Python зависимостей без использования старого кэша Amvera
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
ENV QT_QPA_PLATFORM=offscreen

EXPOSE 8080

CMD ["python", "main.py", "--sport", "football", "--match_id", "prod_match_001", "--agent_host", "localhost:50051", "--dashboard_port", "8080"]
