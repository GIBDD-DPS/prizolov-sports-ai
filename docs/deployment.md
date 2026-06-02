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

After deploy, verify:
- `GET /api/donors/status`
- `GET /api/source-status` (quality + external donor runtime)
- `GET /api/consensus/top`
