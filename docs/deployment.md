# Деплой

## Локально

```bash
docker-compose up --build
# или
pip install -e .
python main.py
```

## Production env profiles (рекомендуемые пресеты)

Для быстрого применения профиля используйте:

```bash
bash scripts/quality_profile_presets.sh balanced
```

Доступные профили:
- `conservative` — максимум надежности, меньше объема линий
- `balanced` — рекомендуемый production режим по умолчанию
- `aggressive` — больше линий и охват, выше волатильность

Примеры применения:

```bash
# Сгенерировать и просмотреть профиль
bash scripts/quality_profile_presets.sh conservative

# Сгенерировать блок в отдельный файл
bash scripts/quality_profile_presets.sh balanced > runtime/quality_profile.env
```

Дальше вставьте переменные в:
- `.env` для локального запуска
- секреты/переменные окружения на платформе деплоя

### Что регулируют профили

- качество входных котировок (`MAX_BOOKMAKER_ODDS_AGE_SECONDS`, `MIN_BOOKMAKERS_PER_EVENT`)
- пороги рекомендаций (`MIN_RECOMMENDATION_PROBABILITY`, `MIN_RECOMMENDATION_EDGE`, `MIN_EVENT_QUALITY_SCORE`)
- анти-корреляцию линий (`MAX_CORRELATED_LINES_PER_EVENT`, `MAX_TOP_RECOMMENDATIONS_PER_EVENT`)
- value-only premium витрину (`VALUE_ONLY_PREMIUM_*`)
- адаптивные пороги (`ADAPTIVE_*`)
- самообучение и time-decay (`SELF_LEARNING_*`)
- CLV-контроль (`CLV_ALERT_NEGATIVE_THRESHOLD`)

## Быстрый старт для production

Если не уверены, используйте `balanced`:

```bash
bash scripts/quality_profile_presets.sh balanced
```


## External donor connectors (production)

For larger donor coverage, configure feed lists in env (JSON arrays):

- `EXTERNAL_DONOR_JSON_FEEDS`
- `EXTERNAL_DONOR_RSS_FEEDS`
- `EXTERNAL_DONOR_TEXT_FEEDS`

Recommended baseline:

```env
EXTERNAL_CONSENSUS_ENABLED=true
EXTERNAL_CONSENSUS_MIN_SOURCES=3
EXTERNAL_DONOR_ENABLE_SYNTHETIC=true
EXTERNAL_DONOR_SIGNAL_LIMIT_PER_EVENT=10
EXTERNAL_DONOR_HTTP_TIMEOUT_SECONDS=5
EXTERNAL_DONOR_HTTP_MAX_BODY_BYTES=850000
EXTERNAL_DONOR_RSS_ITEM_LIMIT=50
EXTERNAL_DONOR_TEXT_ITEM_LIMIT=60
```


Ready donor pack (validated public feeds):
- `docs/external_donor_pack.env` (empty feeds, synthetic off)

After deploy, verify:
- `GET /api/donors/status`
- `GET /api/source-status` (quality + external donor runtime)
- `GET /api/consensus/top`

## The Odds API (Amvera)

Задайте в переменных окружения Amvera (не в git):

- `API_FOOTBALL_KEY` — ключ с https://www.api-football.com/ (заголовок `x-apisports-key`, хост `https://v3.football.api-sports.io`)
- `THE_ODDS_API_KEY` — ключ с https://the-odds-api.com/ (основной источник котировок)
- `REAL_EVENTS_ENABLED=true`

Проверка: `GET /api/source-status` → `real_events.api_key_present: true`, `last_error: null`.

Если `OUT_OF_USAGE_CREDITS` — бесплатные credits закончились. Бэкенд автоматически паузит Odds API на `ODDS_API_BLOCK_SECONDS` (по умолчанию 24ч) и переходит на API-Football / bookmaker scrape без спама в логах. Полностью отключить: `THE_ODDS_API_ENABLED=false` в Amvera.

### Если API-Football `account is suspended`

Аккаунт нужно восстановить на https://dashboard.api-football.com — до этого API не отдаёт матчи. Повторные запросы к API-Football приостанавливаются на 1 час (`API_FOOTBALL_BLOCK_SECONDS`), чтобы не спамить логи.

## Bookmaker scrape (Pari.ru)

When The Odds API/API-Football are unavailable, enable periodic scrape of bookmaker line pages:

```env
BOOKMAKER_SCRAPE_ENABLED=true
BOOKMAKER_SCRAPE_URLS=https://pari.ru/sports/football,https://pari.ru/live/football
BOOKMAKER_SCRAPE_INTERVAL_SECONDS=300
```

- `https://pari.ru/sports/top` is mostly a JS shell
### Pari URL query parameters

| URL | HTTP scrape (Googlebot UA) |
|-----|----------------------------|
| `https://pari.ru/live?dateInterval=5` | Works (~100+ live events) |
| `https://pari.ru/sports/football?dateInterval=5` | Works (~170 prematch/live football) |
| `https://pari.ru/sports?dateInterval=5` | Does **not** work (SPA shell, no teams in HTML) |
| `https://pari.ru/sports?mode=1&dateInterval=5` | Does **not** work (same shell) |

Use sport-specific or `/live` paths instead of bare `/sports?...` for server-side HTML.
; use football/live URLs instead.
- The backend parses `itemprop="homeTeam"` / `awayTeam` from SSR HTML (Googlebot User-Agent).
- For full odds, run a Playwright worker and POST to `/api/ingest/bookmaker-events` with header `X-Bookmaker-Ingest-Secret`.

### Amvera: скрап Pari без ручных переменных

На Amvera задана системная переменная `AMVERA=1`. Если `BOOKMAKER_SCRAPE_ENABLED` не указана,
скрап **включается автоматически** после деплоя `main` (PR #13+).

Явно отключить: `BOOKMAKER_SCRAPE_ENABLED=false`.

### Winline.ru /nearest

Проверено: `https://winline.ru/nearest` отдаёт Angular SPA (~130 KB), **без матчей в HTML**.
Линия подгружается через WebSocket `wss://wss.winline.ru/data_ng?client=newsite&nb=true`.
HTTP-скрап сейчас **не даёт событий** (`WINLINE_SCRAPE_ENABLED=false` по умолчанию).
Статус: `GET /api/source-status` → `bookmaker_scrape.winline.probe`.
