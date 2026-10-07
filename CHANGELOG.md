<!-- ============================================
Copyright (c) 2026
PRIZOLOV SPORTS AI v14.40 (STORE-FRONT OPTIMIZED)
Author: Dm.Andreyanov
Organization: Prizolov Market / Prizolov Lab
============================================ -->

# Changelog

## [14.43] - 2026-10-07

### Fixed
- Amvera: после 14.42 контейнер по-прежнему не стартовал с той же ошибкой (`exec: "uvicorn backend.app.main:app --host 0.0.0.0 --port 8080": executable file not found in $PATH`), хотя в `amvera.yaml` строки `command` уже не было: команда запуска хранится в настройках проекта на Amvera. Добавлен `start.sh` (переход в `backend/` и `exec uvicorn app.main:app`), он же в `CMD` Dockerfile и в `run.command` `amvera.yaml`. Команда одним словом без пробелов запускается и как имя исполняемого файла, и через shell.

## [14.42] - 2026-09-28

### Fixed
- `rebuild_predictions` больше не пересчитывает прогнозы матчей, которые уже начались. The Odds API `/odds` отдаёт и live-события, поэтому прогноз начавшегося матча переписывался по коэффициентам по ходу игры, а сверка в `accuracy_log` засчитывала его как сделанный до матча, и точность была завышена. Теперь после kickoff прогноз остаётся таким, каким был на последнем прогоне до начала; матч, впервые увиденный уже после начала, прогноза не получает.
- Данные `accuracy_log` до этой версии могли включать прогнозы, переписанные по ходу матча, и с новыми не вполне сравнимы.
- Amvera: контейнер не стартовал (`exec: "uvicorn backend.app.main:app --host 0.0.0.0 --port 8080": executable file not found in $PATH`). `run.command` в `amvera.yaml` передавался контейнеру одной строкой как имя исполняемого файла. Строка убрана, запуск идёт по `CMD` из `Dockerfile`. Сама команда тоже была нерабочей: из корня `backend.app.main` падал с `ModuleNotFoundError: No module named 'app'`, потому что код импортирует себя как `app.*`, а статику ищет в `./static`. Теперь контейнер запускается из `backend/` как `uvicorn app.main:app`.

## [14.40] - 2026-09-27

### Added
- Agenomics Q4 (`backend/app/engine/agenomics_evidence.py`): прогноз 1X2 замораживается в EvidenceStore agenomics вместе с Trust Score прогнозирующего агента, когда до начала матча остаётся не больше `AGENOMICS_FREEZE_WINDOW_MINUTES` (45). Выбор и вероятность входят в снимок предсказания с SHA-256.
- После матча `reconcile_finished_events` подтверждает замороженный выбор итоговым счётом из The Odds API `/scores` через `agenomics.record_external_outcome()`: исход Q4, `ground_truth`, ссылка на запись `/scores`. Первый реальный источник Q4 для валидации Agenomics.
- База доказательств: `/data/agenomics_evidence.db` (persistenceMount), настройка `AGENOMICS_EVIDENCE_DB`.
- `backend/tests/`: тесты заморозки и подтверждения (`python -m pytest tests/` из `backend/`).

### Changed
- `agenomics` закреплён на теге `v0.9.6` вместо ветки `main`.

### Notes
- Сверяется замороженный до матча выбор, а не текущая строка `predictions`: `rebuild_predictions` переписывает прогнозы каждый прогон, включая начавшиеся матчи (The Odds API `/odds` отдаёт и live-события), поэтому к моменту сверки строка может отражать коэффициенты по ходу игры. `accuracy_log` по-прежнему сверяет текущую строку.

## [14.38] - 2026-06-10

### Added
- Step 7 storefront: live events + predictions on `backend/static/index.html` (same-origin, no hosting config).
- Next.js `Storefront` client component with retry/timeout/fallback for static export on external hosting.
- `STOREFRONT_ORIGINS` env for CORS when vitrina is on a separate domain.

### Fixed
- `PRODUCT_VERSION` now reads from root `VERSION` file (health banner matches release).

## [14.36] - 2026-06-10

### Added
- Step 6 weighted prediction engine now rebuilds aggregated 1X2 predictions from persisted source odds.
- Parser runner now writes prediction count into run results after each parse cycle.

## [14.34] - 2026-06-10

### Improved
- Predictz parser now degrades gracefully on 403 with fallback data instead of failing the whole source run.
- Parser kickoff slots normalized to rounded UTC hours to reduce duplicate events on repeated runs.

## [14.32] - 2026-06-10

### Fixed
- Allow `POST /api/v1/admin/parse` without header when `API_SECRET` is not configured.

## [14.30] - 2026-06-10

### Added
- Parser DB persistence layer: upsert parsed `events`, `markets`, and `odds` into PostgreSQL.
- Parse source run logs now saved in `parse_logs`, including per-source fetch failures.

## [14.28] - 2026-06-10

### Fixed
- Set Amvera `servicePort` to `80` per platform support guidance to avoid external `503` responses.

## [14.26] - 2026-06-09

### Removed
- Legacy `parser/` tree (integrated in `backend/app/parser/`).
- Duplicate `backend/Dockerfile`, `backend/amvera.yaml`, `amvera.yml`, `amvera.pip.yaml`.
- Unused `shared/` schemas (not imported; markets live in backend).

## [14.22] - 2026-06-08

### Fixed
- Simplified `amvera.yaml` / `amvera.yml`: Docker only, removed erroneous `run.command` with `cd backend`.

## [14.20] - 2026-06-08

### Fixed
- Documented Amvera UI misconfiguration: pip mode pointed at removed root `app/main.py`.
- Added `amvera.pip.yaml` fallback and `docs/AMVERA_UI_FIX.md` with Docker vs pip settings.

## [14.18] - 2026-06-08

### Fixed
- Amvera pip build error on `beautifulsoup4`: removed unused dependency (parsers use httpx + selectolax).
- Added `amvera.yml` duplicate, `ca-certificates` in Dockerfile, explicit PyPI index URL.
- `backend/static/.gitkeep` so Docker COPY succeeds on fresh clone.
- Synced copyright headers to v14.18 across project files.

## [14.16] - 2026-06-08

### Fixed
- Amvera venv conflict: expanded `.gitignore` / `.dockerignore`, deploy docs and `make_amvera_zip.ps1`.
- `verify_project.py` warns if local venv folder exists before upload.

## [14.14] - 2026-06-08

### Added
- Loud startup banner in logs to distinguish v14.14 from legacy v16/pari.ru builds.

## [14.12] - 2026-06-07

### Fixed
- Amvera build: restored root `requirements.txt` with pinned `beautifulsoup4==4.12.3`.
- Dockerfile: upgrade pip/setuptools/wheel before install.

## [14.10] - 2026-06-07

### Added
- `scripts/verify_project.py` — autonomous file/link/import checks.
- `scripts/sync_copyright.py` — sync copyright version headers.
- Parser shared HTTP headers (`app/parser/http_client.py`) for source sites.

### Changed
- All project file headers synced to v14.10.
- Frontend/static placeholders updated to v14.10.

## [14.08] - 2026-06-07

### Changed
- Amvera application name documented as `prizolov-sports`.
- `AMVERA_APP_NAME` config and health endpoint field `amvera_app`.

## [14.06] - 2026-06-07

### Changed
- Single Amvera app: API + parser scheduler in one container.
- Root `amvera.yaml` + `Dockerfile` for monorepo deploy from GitHub.
- Parser moved to `backend/app/parser/` with background scheduler.
- Admin endpoint `POST /api/v1/admin/parse` for manual parser trigger.

## [14.04] - 2026-06-07

### Added
- Amvera CNPG PostgreSQL config: host `amvera-dmandreyanov-cnpg-sports-rw`.
- `POSTGRES_*` env vars or `DATABASE_URL` for backend and parser.
- Parser `db_config.py` for shared DB connection.

## [14.02] - 2026-06-07

### Added
- PostgreSQL/SQLite schema: Sport, Event, Market, Odds, Prediction, ParseSource, ParseLog.
- Alembic migrations with seed data (sports + parse sources).
- FastAPI DB integration: sports, events, predictions endpoints query database.
- Health endpoint reports database connectivity status.

## [14.0] - 2026-06-07

### Added
- Initial STORE-FRONT OPTIMIZED scaffold (backend, parser, frontend, shared).
- FastAPI skeleton with health and placeholder API routes.
- Parser cron skeleton with Forebet, Predictz, Betensured adapters.
- Next.js public storefront skeleton.
- Amvera deployment configs for web and cron projects.

### Removed
- Legacy CV/ONNX/gRPC codebase replaced by prediction platform architecture.
