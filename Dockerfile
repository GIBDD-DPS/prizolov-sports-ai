# ============================================
# Prizolov Sports AI - Headless OS Container
# Version: 7.00 (+1.00: Clean ENTRYPOINT & Env-Driven Config)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at cloud.amvera.ru
# ============================================

FROM python:3.10-slim

# Устанавливаем системные зависимости (совместимые с Debian Trixie)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-dri \
    libglx-mesa0 \
    libglib2.0-0 \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Создаём рабочую директорию
WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем Python-зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Экспортируем порт
EXPOSE 8000

# Команда запуска FastAPI
CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]

ENTRYPOINT ["python", "main.py"]
CMD ["--mock-mode"]
