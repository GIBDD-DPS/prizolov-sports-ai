# Amvera: исправление конфигурации (v16 → v14)

## В чём проблема

В UI Amvera сейчас:

| Параметр | Сейчас (неверно) | Почему не работает |
|----------|------------------|-------------------|
| Окружение | **python + pip** | Старый v16 жил в корневом `app/main.py` |
| `requirementsPath` | `requirements.txt` | Корневой файл — для legacy; приложение в `backend/` |
| `command` | `uvicorn app.main:app ...` | Файла **`app/main.py` в корне нет** (есть `backend/app/main.py`) |

Amvera показывает: *«В коде не найден указанный файл»* — это ожидаемо для ветки `main` после пересборки v14.

В Git уже лежит **`amvera.yaml` с Docker**, но **настройки в UI Amvera перебивают** файл из репозитория.

---

## Вариант A (рекомендуется): Docker

В разделе **Конфигурация** Amvera:

1. **Окружение** → выберите **`docker`** (не python)
2. Удалите или очистите секции `meta.toolchain` / `pip` / `requirementsPath` / `scriptName`
3. В `build` укажите:
   ```yaml
   build:
     dockerfile: Dockerfile
   ```
4. В `run`:
   ```yaml
   run:
     containerPort: 8080
     persistenceMount: /data
   ```
5. **Сохранить** → **Заморозить** ~20 сек → **Пересобрать**

После успеха в логах:
```
=== PRIZOLOV DOCKER START v14.18 ===
PRIZOLOV SPORTS AI v14.18
```

Проверка: `https://prizolov-sports-dmandreyanov.amvera.io/api/v1/health`

---

## Вариант B: остаться на pip

Если Docker в UI недоступен, используйте pip-конфиг из раздела ниже («Вариант B» в `docs/DEPLOY_AMVERA.md`).

```yaml
meta:
  environment: python
  toolchain:
    name: pip
    version: "3.11"

build:
  requirementsPath: backend/requirements.txt

run:
  command: sh -c "cd backend && alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8080 --loop asyncio --workers 1"
  containerPort: 8080
  persistenceMount: /data
```

**Не используйте** `uvicorn app.main:app` без `cd backend` — модуль `app` в корне удалён.

---

## Что НЕ должно быть в логах

```
🚀 PRIZOLOV SPORTS AI v16.0 - QUALITY METRICS
Bookmaker background scrape ... pari.ru ...
```

Это старый контейнер v16; он исчезнет только после успешной сборки v14.

---

## Как читать лог сборки Docker

### Правильный билд (из GitHub `main`)

```
=== PRIZOLOV DOCKERFILE v14.24 (port 8080, no appuser) ===
COPY backend/requirements.txt
EXPOSE 8080
=== PRIZOLOV DOCKER START v14.24 ===
```

### Неправильный билд (старый код в Artifacts Amvera)

```
COPY . .
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", ..., "--port", "8000"]
HEALTHCHECK ... localhost:8000/health
```

Если видите **8000** и **appuser** — Amvera **не взяла** `Dockerfile` из GitHub.

**Что сделать:**
1. **Настройки → Git** — репозиторий `GIBDD-DPS/prizolov-sports-ai`, ветка **`main`**
2. Отключить/удалить ручную загрузку архива в **Code**
3. **Заморозить** проект ~20 сек (очистка Artifacts)
4. **Пересобрать** и снова проверить лог

`containerPort` и `servicePort` должны быть **8080** (не 8000).

---

## GitHub: ветка `main` vs `master`

Amvera по умолчанию делает pull из ветки **`master`**.  
В репозитории основная ветка — **`main`**, поэтому папка **Code** на Amvera могла **не обновляться** и собирать старый `Dockerfile` (appuser, порт 8000).

**Проверьте в Amvera → Репозиторий → подключение GitHub:**
- целевая ветка: **`main`** (или **`master`**, если создали алиас)

**Проверьте Dockerfile в Amvera → Репозиторий → Code:**
- должна быть строка `PRIZOLOV DOCKERFILE v14.24` и `EXPOSE 8080`
- если видите `appuser` и `8000` — замените файл содержимым из GitHub `main` и сохраните
