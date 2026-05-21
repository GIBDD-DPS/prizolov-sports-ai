# Архитектура Prizolov Sports AI

## Обзор

**Prizolov Sports AI** — это модульная, отказоустойчивая система реального времени для компьютерного зрения и аналитики спорта с акцентом на live-рекомендации.

**Версия ядра:** 4.01

## Высокоуровневая схема
[Внешние источники] → data_ingest → core/orchestrator → modules/football → agent_bridge
↓
risk_manager + fallback_db
↓
FastAPI + WebSocket → Frontend (prizolov.ru/sport)
text## Основные компоненты

| Компонент              | Папка               | Назначение |
|------------------------|---------------------|----------|
| **Computer Vision**    | `core/cv/`          | YOLOv10 ONNX, homography, keypoints, ball tracking, occlusion filter |
| **Orchestrator**       | `core/`             | Главный цикл обработки, Smart Batching |
| **Analytics Engine**   | `modules/`          | Poisson, xG, momentum, Dixon-Coles и др. |
| **Risk & Money Mgmt**  | `core/risk_manager.py` | Управление рисками, bankroll |
| **Agent Bridge**       | `agent_bridge/`     | Связь с основной агент-системой v3.03 |
| **API & WebSocket**    | `main.py`           | FastAPI + WebSocket endpoint |
| **Frontend**           | `assets/js/`        | prizolov-live-feed.js |

## Технологический стек

- **Backend**: Python 3.11+, FastAPI, aiohttp, asyncio
- **CV**: ONNX Runtime, OpenCV, NumPy
- **Модели**: YOLOv10, custom homography
- **Данные**: WebSocket, gRPC, fallback SQLite/JSON
- **Деплой**: Docker, docker-compose, Amvera Cloud

## Поток данных (Live)

1. Получение raw-фреймов / данных
2. Computer Vision Pipeline
3. Расчёт метрик (possession, xG, danger attacks)
4. Аналитический модуль → генерация линии
5. Risk assessment
6. Отправка через WebSocket на сайт

## Масштабируемость

- Поддержка нескольких матчей одновременно (в разработке)
- GPU-ready (ONNX)
- Memory Balancer + Circuit Breaker
