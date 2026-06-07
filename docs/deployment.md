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

## Events source (Amvera)

The Odds API, API-Football и OddsPapi удалены из бэкенда. События витрины берутся из **bookmaker scrape** (Pari.ru и ingest).

Проверка после деплоя:

```bash
curl -s https://YOUR_APP/api/source-status | jq '.events_source'
```

Ожидается: `primary: "bookmaker_scrape"`, `removed_providers` содержит `the_odds_api`, `api_football`, `oddspapi`.

Удалите из переменных Amvera (если ещё заданы): `THE_ODDS_API_KEY`, `API_FOOTBALL_KEY`, `ODDSPAPI_*`, `REAL_EVENTS_*`.

Рекомендуемый лёгкий режим для CPU:

```env
BOOKMAKER_SCRAPE_ENABLED=true
BOOKMAKER_SCRAPE_REQUEST_PATH_SYNC=false
BOOKMAKER_SCRAPE_INTERVAL_SECONDS=900
EXTERNAL_CONSENSUS_ENABLED=false
STORE_CACHE_TTL_SECONDS=120
```

## Bookmaker scrape (Pari.ru)

Primary source for storefront events — periodic scrape of bookmaker line pages:

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
