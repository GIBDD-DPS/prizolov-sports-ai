# ============================================
# Prizolov Sports AI - Headless OS Container
# Version: 7.00 (+1.00: Clean ENTRYPOINT & Env-Driven Config)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at cloud.amvera.ru
# ============================================

FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-dri \
    libglx-mesa0 \
    libglib2.0-0 \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# ВАЖНО: НИКАКИХ ENTRYPOINT
# Запускаем только uvicorn
CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]

ENTRYPOINT ["python", "main.py"]
CMD ["--mock-mode"]
