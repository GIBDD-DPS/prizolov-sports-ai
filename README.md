# Prizolov Sports AI

**Автономная AI-система аналитики спорта** (фокус — футбол) с live-рекомендациями для ставок и глубокой компьютерным зрением.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-ready-blue)](https://www.docker.com)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

## ✨ Возможности

- Реал-тайм компьютерное зрение (YOLOv10 ONNX + homography + keypoints)
- Продвинутая футбольная аналитика (xG, Poisson + Dixon-Coles, momentum, dominance)
- Live AI-рекомендации с расчётом Value
- WebSocket дашборд + fallback-система
- Risk Management и Money Management
- Поддержка нескольких видов спорта

## 🚀 Быстрый старт

### Локальный запуск

```bash
git clone https://github.com/GIBDD-DPS/prizolov-sports-ai.git
cd prizolov-sports-ai

# Вариант 1: Docker (рекомендуется)
docker-compose up --build

# Вариант 2: Локально
pip install -e .
cp .env.example .env
python main.py
```

### Деплой на Amvera
Просто запушь — `amvera.yml` уже настроен.

## 📁 Структура проекта

```bash
├── core/                 # Ядро (CV pipeline, orchestrator, risk manager...)
├── modules/              # Аналитика по видам спорта (football.py — главный)
├── agent_bridge/         # Интеграция с агент-системой v3.03
├── assets/js/            # Frontend (WebSocket дашборд)
├── data_ingest/          # Сбор данных
├── proto/                # gRPC
├── tests/                # Тесты
├── docs/                 # Документация
├── main.py               # Точка входа (FastAPI + WS)
└── docker-compose.yml
```

## 🛠 Основные компоненты

- **Computer Vision**: ONNX + homography + occlusion handling
- **Analytics**: Poisson + live adjustments + xG
- **Dashboard**: https://prizolov.ru/sport/
- **Reliability**: Fallback DB, memory balancer, circuit breakers

## 📈 Roadmap

- [ ] Расширение рынков (corners, cards, player props)
- [ ] Тактические карты и radar
- [ ] Много-матчевый режим
- [ ] Генеративные описания
- [ ] Мобильное приложение

## 📄 Документация

- [API Endpoints](docs/api.md)
- [Архитектура](docs/architecture.md)
- [Модели](docs/models.md)

**Автор**: Dm.Andreyanov (GIBDD-DPS)  
**Проект**: Prizolov Lab
