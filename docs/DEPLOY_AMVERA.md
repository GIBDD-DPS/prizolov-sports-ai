<!-- ============================================
Copyright (c) 2026
PRIZOLOV SPORTS AI v14.16 (STORE-FRONT OPTIMIZED)
Author: Dm.Andreyanov
Organization: Prizolov Market / Prizolov Lab
============================================ -->

# Деплой на Amvera — проект prizolov-sports

## Главное: не загружайте venv

Amvera **сама** создаёт окружение из `requirements.txt`.  
Папки `venv/`, `.venv/` **нельзя** класть в архив или Git.

Ошибки при загрузке venv:
- `Permission denied: '/app/venv'`
- `No module named pip.__main__`
- Сборка падает или крутится старый код

---

## Если деплой через архив (Upload)

1. **Удалите** локально (не из Git, просто с диска):
   ```powershell
   Remove-Item -Recurse -Force venv, .venv, backend\venv -ErrorAction SilentlyContinue
   ```
2. Соберите чистый ZIP **без venv**:
   ```powershell
   .\scripts\make_amvera_zip.ps1
   ```
3. Загрузите `deploy-amvera.zip` в Amvera

---

## Если venv «застрял» в Artifacts Amvera

1. **Настройки** → **Заморозить проект**
2. Подождите **~20 секунд** (папка venv должна удалиться)
3. **Пересобрать**

Если не помогло — создайте **новый** проект Amvera и привяжите GitHub.

---

## Рекомендуется: GitHub (без venv)

1. Репозиторий: `GIBDD-DPS/prizolov-sports-ai`, ветка `main`
2. venv уже в `.gitignore` — в GitHub его нет
3. Окружение: **Docker** (`amvera.yaml` + `Dockerfile` в корне)

После успешного деплоя в логах:
```
=== PRIZOLOV DOCKER START v14.18 ===
PRIZOLOV SPORTS AI v14.14+
```
**Не должно быть:** `v16.0`, `pari.ru`, `Bookmaker background`

---

## Ошибка `beautifulsoup4>=4.12.0 (from versions: none)`

Это значит Amvera собирает **старый архив в режиме pip**, а не Docker из GitHub.

| Признак | Старый архив (pip) | Правильный деплой (Docker) |
|---------|-------------------|----------------------------|
| В логах | `pip install`, `beautifulsoup4>=4.12.0` | `=== PRIZOLOV DOCKER START ===` |
| Конфиг | нет `amvera.yaml` / `Dockerfile` в корне ZIP | `amvera.yaml` + `Dockerfile` в корне |
| Источник | ручная загрузка старого ZIP | GitHub `main` |

**Что сделать:**
1. Привязать GitHub `GIBDD-DPS/prizolov-sports-ai`, ветка `main`
2. Или загрузить свежий ZIP: `.\scripts\make_amvera_zip.ps1`
3. Заморозить проект 20 сек (очистить venv в Artifacts)
4. Пересобрать

В v14.18 `beautifulsoup4` удалён из requirements — он не использовался в коде.

---

## Secrets

```
POSTGRES_HOST=amvera-dmandreyanov-cnpg-sports-rw
POSTGRES_USER=...
POSTGRES_PASSWORD=...
POSTGRES_DB=sports
POSTGRES_SSLMODE=disable
PARSER_ENABLED=true
```
