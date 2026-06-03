# Melbet calendar (`/ru/sport/calendar`)

## URL

- https://melbet.ru/ru/sport/calendar?filter=e30=
- `filter=e30=` — base64 JSON `{}` (пустой фильтр = **все виды спорта** в календаре).

## Что можно взять для витрины

| Источник | Данные | Статус в проекте |
|----------|--------|------------------|
| HTML календаря | Команды, лига, live/прематч (если есть в SSR/JSON) | `melbet_scrape_source.py`, `MELBET_SCRAPE_ENABLED=true` |
| Partner API `GET /sports/{version}/GetEvents` | События по `sportType` (футбол=1, хоккей=4, баскетбол=2, …) | Нужны `MELBET_SPORTS_API_BASE` + `MELBET_API_TOKEN` (JWT от Melbet) |
| Pari.ru scrape | 16 видов спорта, коэффициенты в HTML | Основной источник на Amvera |

## Ограничения

- С серверов вне РФ Melbet часто отдаёт **403 / «сайт недоступен в вашей стране»** (Cloudflare).
- Публичного API без партнёрского токена нет; календарь в браузере грузит данные после JS.

## Env

```env
MELBET_SCRAPE_ENABLED=false
MELBET_CALENDAR_URL=https://melbet.ru/ru/sport/calendar?filter=e30=
# MELBET_SPORTS_API_BASE=https://...
# MELBET_API_TOKEN=...
```

## Почему на витрине был только футбол

На Amvera в `BOOKMAKER_SCRAPE_URLS` стояли **только 3 football URL** из старого `.env.example`. Код теперь автоматически расширяет такой список до **17 страниц Pari** (live + 16 sports).
