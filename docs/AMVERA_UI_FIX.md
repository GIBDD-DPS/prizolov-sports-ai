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

Если Docker в UI недоступен, замените конфиг на содержимое файла **`amvera.pip.yaml`**:

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
