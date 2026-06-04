# Prizolov Sports AI v15 — аналитический контур

Цель: **не больше агентов**, а измеримое качество ставок и линии.

## Модули (в репозитории: `app/analytics/`)

| Модуль | Файл | Назначение | Статус |
|--------|------|------------|--------|
| **xG / xGA** | `xg_model.py` | Ожидаемые голы/пропущенные по матчу (live + прематч) | v1 в API |
| **CLV** | `clv_tracker.py` | Closing Line Value: ставка vs закрывающая линия | v1, JSON-ledger |
| **Value Detector** | `value_detector.py` | edge = P модели − implied рынка | v1, в summary |
| **ROI Monitor** | `roi_monitor.py` | Виртуальный банк, ROI%, open/settled | v1 |
| **Line Movement** | `line_movement.py` | Снимки PARI + Pinnacle, дельта коэф. | v1 PARI; Pinnacle — по фиду |

## API

- `GET /api/analytics/v15/summary` — сводка всех модулей
- `GET /api/analytics/value-detector?limit=50`
- `GET /api/analytics/line-movement?limit=40`
- `GET /api/analytics/roi`
- `GET /api/analytics/clv`

Пайплайн вызывается при сборке витрины (`_build_storefront_payload`): xG + снимки PARI + value + CLV/ROI.

## Дорожная карта (фазы)

### Фаза 1 — сейчас (MVP)
- [x] Каркас модулей + persistence `runtime/analytics_state.json`
- [x] Value Detector на рекомендациях витрины
- [x] История линий PARI при каждом scrape
- [ ] Виджет: блок «Value / CLV / движение линии»

### Фаза 2 — данные
- [ ] xG v2: Understat / API-Football shots → xG
- [ ] Pinnacle: Odds API / партнёрский фид (`PINNACLE_ODDS_ENABLED`)
- [ ] Закрывающая линия CLV (последний снимок перед стартом)

### Фаза 3 — продакшен
- [ ] PostgreSQL вместо JSON для CLV/ROI
- [ ] Алерты Telegram при value + движении линии > N%
- [ ] Бэктест ROI по истории снимков

## Env

```env
ANALYTICS_STATE_PATH=runtime/analytics_state.json
PINNACLE_ODDS_ENABLED=false
# EXCLUDED_STOREFRONT_SPORTS=esports
```

## Связь с `modules/football.py`

Полноценная Dixon–Coles / Poisson xG уже есть в `modules/football.py` (CV-пайплайн).  
`analytics/xg_model.py` — **лёгкий слой для витрины**; в фазе 2 объединить с FootballAnalyticsModule.
