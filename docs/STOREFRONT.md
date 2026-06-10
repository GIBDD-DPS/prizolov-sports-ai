# Витрина (Step 7)

## Вариант A — на том же Amvera (рекомендуется)

Ничего настраивать не нужно:

- откройте `https://sport-ai-dmandreyanov.amvera.io/`
- витрина берёт API с того же домена (`/api/v1/...`)

## Вариант B — отдельный хостинг (статика)

1. Соберите фронт:
   ```bash
   cd frontend
   set NEXT_PUBLIC_API_URL=https://sport-ai-dmandreyanov.amvera.io/api/v1
   npm run build
   ```
   Папка `frontend/out/` — загрузите на любой статический хостинг.

2. В Amvera → Secrets добавьте:
   ```
   STOREFRONT_ORIGINS=https://ваш-сайт.example
   ```

3. Или используйте один файл `backend/static/index.html` на внешнем хосте с параметром:
   ```
   https://ваш-сайт.example/?api=https://sport-ai-dmandreyanov.amvera.io/api/v1
   ```
   (нужен CORS в `STOREFRONT_ORIGINS`)

## Поведение при сбоях

- таймаут 15 с, до 2 повторов
- при ошибке показывается «Данные временно недоступны», сайт не падает
