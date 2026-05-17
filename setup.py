# setup.py
# ============================================
# Prizolov Sports AI - Setup
# Version: 3.01 (Major Architecture Upgrade)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

from setuptools import setup, find_packages

setup(
    name="prizolov-sports-ai",
    version="3.01.0",
    description="High-performance Sports Computer Vision & Broad Line Analytics engine for Prizolov Agent OS",
    author="Dm.Andreyanov",
    organization="Prizolov Market / Prizolov Lab",
    packages=find_packages(exclude=["tests*", "docs*"]),
    install_requires=[
        # --- Базовая математика и обработка данных ---
        "numpy>=1.24.0",
        "pandas>=2.0.0",
        "pydantic>=2.5.0",
        "scipy>=1.10.0",
        
        # --- Компьютерное зрение и Трекинг ---
        "opencv-python-headless>=4.8.0.0",
        "ultralytics>=8.1.0",           # YOLOv10 и базовый трекинг (ByteTrack/BoT-SORT)
        "filterpy>=1.4.5",              # Фильтр Кальмана для высокоскоростного трекинга шайбы/мяча
        
        # --- Транспортный уровень (Интеграция с Prizolov Agent OS) ---
        "grpcio>=1.55.0",               # Высокопроизводительный gRPC транспорт для Live-данных
        "grpcio-tools>=1.55.0",         # Инструменты компиляции proto-файлов
        
        # --- Системные утилиты ---
        "tqdm>=4.65.0",
        "pyyaml>=6.0.0",
    ],
    extras_require={
        "gpu": [
            "onnxruntime-gpu>=1.16.0",   # Для инференса моделей на GPU через ONNX/TensorRT
        ],
    },
    python_requires=">=3.9",            # Поддержка современного тайпинга и оптимизированной асинхронности
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
