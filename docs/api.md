# API и WebSocket

## WebSocket Endpoint

**URL:** `wss://prizolov.ru/ws/sport`

### Основной Live-пакет

См. `docs/api_specification.json`

### Пример сообщения

```json
{
  "match_id": "match_12345",
  "sport": "football",
  "game_time": "67:42",
  "timestamp_ms": 1747850000000,
  "ball_state": { ... },
  "metrics": { ... },
  "line_data": { ... },
  "ai_recommendations": [
    {
      "market": "TO 2.5",
      "probability": 0.68,
      "odds": 1.92,
      "value": 0.12,
      "confidence": 0.74,
      "reasoning": "Высокий xG + momentum Team A"
    }
  ]
}
REST Endpoints (FastAPI)

GET /health — статус системы
GET /matches/live — список live-матчей
POST /analyze — разовый анализ матча
GET /models/status — статус загруженных моделей

Документация OpenAPI доступна по /docs при локальном запуске.

## Self-learning API

- `GET /api/learning/status` — текущий статус самообучения (по видам спорта).
- `POST /api/learning/feedback` — запись факта исхода прогноза.

Пример payload для feedback:

```json
{
  "sport": "football",
  "predicted_probability": 0.63,
  "outcome": true
}
```

## Auto feedback worker (cron)

Добавлен скрипт: `scripts/auto_feedback_worker.py`.

Что делает:
- запрашивает события из `/api/all-events`;
- сохраняет рекомендации в локальный state (`runtime/auto_feedback_worker_state.json`);
- после задержки `--settle-seconds` пытается определить исход для `H2H` по score и отправляет в `/api/learning/feedback`;
- перед отправкой делает preflight `GET /api/learning/status`, чтобы не спамить ошибками, если learning endpoint еще не задеплоен;
- при флаге `--bootstrap-when-unresolved` может отправлять bootstrap feedback, если score-резолв недоступен.

Базовый запуск:

```bash
python3 scripts/auto_feedback_worker.py \
  --api-base-url "http://127.0.0.1:8080" \
  --settle-seconds 7200 \
  --max-feedback-per-run 25
```

Боевой режим (без bootstrap, только подтвержденные исходы):

```bash
python3 scripts/auto_feedback_worker.py \
  --api-base-url "https://prizolov-sports-dmandreyanov.amvera.io" \
  --settle-seconds 7200 \
  --max-feedback-per-run 25
```

Пример cron (каждые 10 минут):

```cron
*/10 * * * * cd /workspace && /usr/bin/python3 scripts/auto_feedback_worker.py --api-base-url "http://127.0.0.1:8080" >> /workspace/logs/auto_feedback_worker.log 2>&1
```

## Quality filters for runtime events

`/api/source-status` возвращает блок `quality_filters` с активными настройками фильтрации:
- `supported_runtime_sports`
- `min_bookmakers_per_event`
- `min_recommendation_probability`
- `min_event_quality_score`
- `max_recommendations_per_event`
- `max_upcoming_hours`


## Event ranking and storefront output

`GET /api/all-events` поддерживает витринные фильтры и ранжирование:
- `sport` — код вида спорта (например, `football`)
- `min_quality` — минимальный `quality_score`
- `min_probability` — минимальная вероятность top-рекомендации
- `sort_by` — `priority | quality | probability | freshness | time`
- `limit` — максимум событий
- `recommendations_only` — только события с рекомендациями
- `include_top` — включать ли плоский `top_recommendations`
- `top_limit` — лимит top-рекомендаций

Ответ включает:
- `events` (с `display_priority`, `top_probability`, `top_recommendation`)
- `meta` (распределение по видам спорта и средние показатели)
- `top_recommendations` (готовый список для блока "лучшие ставки")

Отдельный endpoint витрины:
- `GET /api/recommendations/top` — плоский список лучших рекомендаций
  - параметры: `lang`, `sport`, `limit`, `min_probability`
