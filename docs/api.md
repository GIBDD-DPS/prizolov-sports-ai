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
  "ball_state": {},
  "metrics": {},
  "line_data": {},
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
```

---

## REST Endpoints (FastAPI)

### Общие параметры витрины для value-only premium lines

Эти query-параметры поддерживаются в `POST /api/state`, `POST /get-ai-sports.php`,
`GET /api/all-events`, `GET /api/events/{sport}`, `GET /api/sports`,
`GET /api/recommendations/top`:

- `premium_only` (`bool`, default: `false` для большинства endpoint, `true` для `/api/recommendations/top`)  
  Включает жесткий режим, где остаются только premium-линии.
- `min_edge` (`float`, default: `0.08`)  
  Минимальный edge линии. Формула edge: `probability * coefficient - 1`.
- `min_bookmakers_support` (`int`, default: `4`)  
  Минимальная поддержка линии по количеству БК.
- `max_recommendations_per_event` (`int`, default: `6`)  
  Верхний лимит линий на событие.

### `GET /health`

Проверка статуса системы.

### `GET /api/source-status`

Служебный endpoint состояния источника данных и активных фильтров качества.

Пример ответа:

```json
{
  "status": "ok",
  "source": "live_events_static_seed",
  "events_total": 14,
  "quality_filters": {
    "premium_min_edge": 0.08,
    "premium_min_bookmakers_support": 4,
    "max_recommendations_per_event": 6
  },
  "features": {
    "premium_lines_mode": true,
    "edge_scoring": true,
    "bookmakers_support": true
  },
  "timestamp": "2026-06-02T17:00:00+00:00"
}
```

### `POST /api/state`

Возвращает 1 матч (верхний по ранжированию) и его рекомендации с учетом фильтров.

Новые поля рекомендаций:

- `edge`
- `bookmakers_support`
- `value_score`
- `is_premium`
- `selection_tier`

Также ответ содержит:

- `filters` — фактически примененные фильтры
- `features` — readiness-флаги для фронтенда

### `POST /get-ai-sports.php`

Совместимый endpoint для виджета/прокси. Поведение аналогично `POST /api/state`.

### `GET /api/all-events`

Возвращает список событий и обогащенные рекомендации.

Доп. параметр:
- `limit` (`int`, optional) — ограничить число событий в ответе.

### `GET /api/events/{sport}`

Возвращает события только указанного вида спорта (с теми же фильтрами premium-режима).

### `GET /api/recommendations/top`

Плоский список лучших линий по всем событиям.  
По умолчанию `premium_only=true`, то есть endpoint ориентирован на витрину value-only premium lines.

Доп. параметр:
- `limit` (`int`, default: `20`) — ограничение числа строк рекомендаций.

### `GET /api/sports`

Возвращает агрегированный список видов спорта по текущему набору отфильтрованных событий.

---

OpenAPI документация доступна по `/docs` при локальном запуске.
