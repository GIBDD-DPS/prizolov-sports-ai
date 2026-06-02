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
