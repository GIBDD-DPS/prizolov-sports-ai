# setup.py
# ============================================
# Prizolov Sports AI - Setup
# Version: 4.01 (Social Sentiment & Global AI Upgrade)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at prizolov.ru
# ============================================

from setuptools import setup, find_packages

setup(
    name="prizolov-sports-ai",
    version="4.01.0",
    description="Next-Gen Sports CV, Broad Line Analytics & Sentiment Mining Engine for Prizolov Agent OS",
    author="Dm.Andreyanov",
    organization="Prizolov Market / Prizolov Lab",
    packages=find_packages(exclude=["tests*", "docs*"]),
    install_requires=[
        # --- Базовая математика и обработка данных ---
        "numpy>=1.26.0",
        "pandas>=2.1.0",
        "pydantic>=2.6.0",
        "scipy>=1.11.0",
        "scikit-learn>=1.3.0",          # Для кластеризации капперских трендов и аномалий
        
        # --- Компьютерное зрение и Трекинг ---
        "opencv-python-headless>=4.9.0.0",
        "ultralytics>=8.2.0",           # YOLOv10 / YOLOv11 инференс
        "filterpy>=1.4.5",              # Фильтр Кальмана для высокоскоростного трекинга
        
        # --- Парсинг, Скрапинг и Сеть ---
        "httpx>=0.26.0",                # Асинхронный HTTP-клиент для сбора прогнозов
        "beautifulsoup4>=4.12.0",       # Парсинг спортивных верификаторов и форумов
        "redis>=5.0.0",                 # Live-кэш для профилей проходимости и сентимента
        
        # --- Обработка Текста и ИИ-Аналитика (NLP/LLM) ---
        "transformers>=4.38.0",         # Токенайзеры и классификаторы сентимента (BERT/RoBERTa)
        "torch>=2.2.0",                 # Тензорная база для NLP и CV моделей
        
        # --- Transport (Интеграция с Prizolov Agent OS) ---
        "grpcio>=1.62.0",               # Высокопроизводительный gRPC транспорт
        "grpcio-tools>=1.62.0",
        
        # --- Системные утилиты ---
        "tqdm>=4.66.0",
        "pyyaml>=6.0.1",
    ],
    extras_require={
        "gpu": [
            "onnxruntime-gpu>=1.17.0",
        ],
    },
    python_requires=">=3.10",           # Повышено до 3.10 для нативной поддержки новых фич typing и match-case
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
