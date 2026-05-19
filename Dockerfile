# ============================================
# Prizolov Sports AI - Headless OS Container
# Version: 7.00 (+1.00: Clean ENTRYPOINT & Env-Driven Config)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at cloud.amvera.ru
# ============================================

FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx libglib2.0-0 libgl1 gcc build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1 \
    QT_QPA_PLATFORM=offscreen \
    MOCK_MODE=true \
    DISCOVERY_INTERVAL=45

EXPOSE 8080

# ENTRYPOINT гарантирует, что любые CMD-аргументы добавятся после python main.py
ENTRYPOINT ["python", "main.py"]
CMD ["--mock-mode"]
