<!-- ============================================
Copyright (c) 2026
PRIZOLOV SPORTS AI v14.40 (STORE-FRONT OPTIMIZED)
Author: Dm.Andreyanov
Organization: Prizolov Market / Prizolov Lab
============================================ -->

# PRIZOLOV SPORTS AI v14.08

Public sports prediction platform with weighted forecasts for football (MVP), hockey, basketball, and other sports.

**Author:** Dm.Andreyanov  
**Organization:** Prizolov Market / Prizolov Lab  
**Production URL:** https://prizolov-sports-dmandreyanov.amvera.io

## Structure

| Path | Role |
|------|------|
| `amvera.yaml` + `Dockerfile` | **Single Amvera app** (API + parser scheduler) |
| `backend/app/` | FastAPI, DB models, parser (`app/parser/`) |
| `frontend/` | Next.js storefront (Step 7, not deployed yet) |

## Markets (MVP)

- 1X2 (П1 / X / П2)
- Totals (goals)
- Yellow cards (ЖК)
- Corners (угловые)

## Local development

```bash
cd backend
pip install -r requirements.txt
python -m alembic upgrade head
uvicorn app.main:app --reload --port 8080

# Manual parser run
python -m app.parser.runner
```

## Проверка проекта (автоматически)

```bash
python scripts/verify_project.py
python scripts/sync_copyright.py   # синхронизация v14.x в headers
```

## Amvera — одно приложение

### 1. Создать проект
- [cloud.amvera.ru](https://cloud.amvera.ru) → проект **`prizolov-sports`** (тип **Приложение**)

### 2. Подключить GitHub
- Привязать репозиторий `GIBDD-DPS/prizolov-sports-ai`
- Amvera найдёт **`amvera.yaml`** и **`Dockerfile`** в **корне** репозитория

### 3. Переменные окружения (Secrets)

```env
POSTGRES_HOST=amvera-dmandreyanov-cnpg-sports-rw
POSTGRES_PORT=5432
POSTGRES_USER=<из вкладки Инфо БД>
POSTGRES_PASSWORD=<из вкладки Инфо БД>
POSTGRES_DB=sports
POSTGRES_SSLMODE=disable
PUBLIC_URL=https://prizolov-sports-dmandreyanov.amvera.io
API_SECRET=<ваш_секрет>
PARSER_ENABLED=true
PARSER_INTERVAL_MINUTES=30
PARSER_RUN_ON_STARTUP=true
```

### 4. Домен
- Привязать: `prizolov-sports-dmandreyanov.amvera.io`
- Порт: **8080**

### 5. Что происходит при старте
1. `alembic upgrade head` — миграции БД
2. `uvicorn` — API + сайт
3. **Фоновый парсер** — каждые 30 мин (Forebet, Predictz, Betensured)

### 6. Проверка

```
GET https://prizolov-sports-dmandreyanov.amvera.io/api/v1/health
```

Ручной запуск парсера:

```
POST https://prizolov-sports-dmandreyanov.amvera.io/api/v1/admin/parse
Header: X-Api-Secret: <API_SECRET>
```


### Если health возвращает 503

1. Amvera → проект **`prizolov-sports`** → **Логи сборки** и **Логи приложения**
2. Проверьте Secrets: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
3. Убедитесь, что репозиторий привязан к корню (`amvera.yaml` + `Dockerfile`)

## Disclaimer

Predictions are for informational purposes only and do not constitute betting advice.

## Versioning

- Small changes: +0.02
- Global changes: +1.02
- 
