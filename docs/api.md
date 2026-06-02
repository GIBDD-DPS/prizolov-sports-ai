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
- `GET /api/learning/metrics` — расширенные метрики калибровки (Brier, calibration gap, ROI, recent feedback, trend windows, alerts, storefront policy preview).
- `POST /api/learning/feedback` — запись факта исхода прогноза.

Пример payload для feedback:

```json
{
  "sport": "football",
  "predicted_probability": 0.63,
  "outcome": true,
  "coefficient": 1.9,
  "closing_coefficient": 1.82,
  "event_id": "match_123",
  "line": "H2H: Team A",
  "source": "auto_feedback_worker"
}
```

## Auto feedback worker (cron)

Добавлен скрипт: `scripts/auto_feedback_worker.py`.

Что делает:
- запрашивает события из `/api/all-events`;
- сохраняет рекомендации в локальный state (`runtime/auto_feedback_worker_state.json`);
- после задержки `--settle-seconds` пытается определить исход для `H2H` по score и отправляет в `/api/learning/feedback`;
- для CLV отправляет пару `coefficient` (opening) + `closing_coefficient` (последняя доступная линия);
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
- `min_recommendation_coefficient`
- `min_recommendation_edge`
- `max_lines_per_market`
- `max_correlated_lines_per_event`
- `max_top_recommendations_per_event`
- `max_bookmaker_odds_age_seconds`
- `bookmaker_weight_default`
- `bookmaker_weight_overrides_count`
- `sport_market_threshold_overrides_count`
- `effective_min_recommendation_probability`
- `adaptive_threshold_enabled`
- `adaptive_threshold_min_feedback`
- `min_event_quality_score`
- `max_recommendations_per_event`
- `max_upcoming_hours`
- `value_only_premium_enabled`
- `value_only_premium_min_edge`
- `value_only_premium_min_bookmakers_support`
- `self_learning_decay_enabled`
- `self_learning_decay_half_life_hours`
- `clv_alert_negative_threshold`


## Event ranking and storefront output

`GET /api/all-events` поддерживает витринные фильтры и ранжирование:
- `sport` — код вида спорта (например, `football`)
- `min_quality` — минимальный `quality_score`
- `min_probability` — минимальная вероятность top-рекомендации
- `sort_by` — `priority | quality | probability | freshness | time | auto`
- `policy_mode` — `auto | normal | guarded | degraded` (ручной override режима витрины)
- `adaptive_policy` — `true/false` (включать/отключать adaptive storefront-логику для запроса)
- `limit` — максимум событий
- `recommendations_only` — только события с рекомендациями
- `include_top` — включать ли плоский `top_recommendations`
- `top_limit` — лимит top-рекомендаций
- `premium_only` — value-only режим (оставляет только premium-линии)
- `premium_min_edge` — порог edge для premium-линий
- `premium_min_bookmakers_support` — минимальная bookmaker-поддержка premium-линии

Ответ включает:
- `events` (с `display_priority`, `top_probability`, `top_recommendation`)
  - рекомендации включают `weighted_bookmakers_support`, `no_vig_probability`, `market_overround`
- `meta` (распределение по видам спорта и средние показатели)
- `top_recommendations` (готовый список для блока "лучшие ставки")
- `filters.requested` / `filters.effective` (что запросил клиент и что применилось с учетом adaptive policy)
- `filters.value_only` (requested/effective value-only premium настройки)
- `readiness_flags` (feature/readiness-флаги для фронтенда во время rollout)
- `storefront_policy` (режим витрины: `normal | guarded | degraded`)
- `storefront_policy_context` (requested mode, adaptive on/off, base policy mode)

Отдельный endpoint витрины:
- `GET /api/recommendations/top` — плоский список лучших рекомендаций
  - параметры: `lang`, `sport`, `limit`, `min_probability`, `policy_mode`, `adaptive_policy`, `premium_only`, `premium_min_edge`, `premium_min_bookmakers_support`
  - каждая рекомендация включает `edge`, `bookmakers_support`, `weighted_bookmakers_support`, `no_vig_probability`, `market_overround`, `is_premium`, `selection_tier`


Value-only premium lines режим:
- доступен в `POST /api/state`, `POST /get-ai-sports.php`, `GET /api/all-events`, `GET /api/events/{sport}`, `GET /api/recommendations/top`
- включается через `premium_only=true`
- настраивается параметрами `premium_min_edge` и `premium_min_bookmakers_support`
- в ответах возвращаются `filters.value_only` и `readiness_flags` для безопасного frontend-rollout


Быстрые/средние/продвинутые улучшения в рантайме:
- no-vig вероятности считаются на уровне маркетов (учет overround)
- stale-guard отбрасывает устаревшие котировки (`max_bookmaker_odds_age_seconds`)
- поддержка букмекеров учитывает веса (`weighted_bookmakers_support`)
- пороги рекомендаций адаптируются по спорту/рынку (`SPORT_MARKET_THRESHOLD_OVERRIDES`)
- self-learning поддерживает time-decay веса (`SELF_LEARNING_DECAY_*`)
- CLV (opening vs closing) собирается и попадает в learning/metrics
- correlation-guard ограничивает число сильно связанных линий на событие
- готовые production пресеты: `bash scripts/quality_profile_presets.sh {conservative|balanced|aggressive}`
- рекомендуемый профиль для старта: `balanced`


Параметры `GET /api/learning/metrics`:
- `recent_limit` — сколько последних feedback записей вернуть
- `recent_window_hours` — окно recent для трендов
- `baseline_window_hours` — baseline окно для сравнения
- `alert_min_samples` — минимальное число samples для алертов деградации

Ответ включает блоки:
- `quality_threshold` (базовый и эффективный порог вероятности с адаптацией по метрикам)
- `windows` (`recent`, `baseline`, `trend_delta`) включая `clv_avg`
- `alerts` (сигналы стабильности/деградации качества, включая CLV)


Адаптивный порог рекомендаций (runtime):
- `ADAPTIVE_THRESHOLD_ENABLED`
- `ADAPTIVE_THRESHOLD_MIN_FEEDBACK`
- `ADAPTIVE_MIN_PROBABILITY_FLOOR`
- `ADAPTIVE_MIN_PROBABILITY_CEIL`

Текущий эффективный порог доступен в `/api/source-status` через `quality_filters.effective_min_recommendation_probability`.


Адаптивный режим витрины (storefront):
- `STOREFRONT_ADAPTIVE_MODE_ENABLED`
- `STOREFRONT_RECENT_WINDOW_HOURS`
- `STOREFRONT_BASELINE_WINDOW_HOURS`
- `STOREFRONT_ALERT_MIN_SAMPLES`
- `STOREFRONT_DEGRADED_MIN_PROBABILITY`
- `STOREFRONT_DEGRADED_MIN_QUALITY`
- `STOREFRONT_DEGRADED_MAX_EVENTS`

В degraded-режиме API автоматически усиливает фильтрацию и сортировку по качеству для более надежной выдачи.

`GET /api/learning/metrics` также поддерживает `policy_mode` и `adaptive_policy` для preview storefront-режима в аналитике.


Расширение линий ставок:
- рекомендации агрегируются по нескольким букмекерам и рынкам (`h2h`, `totals`, `spreads`),
- отбор приоритизирует линии с высокой проходимостью и высоким коэффициентом,
- поддерживается диверсификация по рынкам (`max_lines_per_market`) и увеличенный лимит `max_recommendations_per_event`.
