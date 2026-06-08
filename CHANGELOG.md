<!-- ============================================
Copyright (c) 2026
PRIZOLOV SPORTS AI v14.10 (STORE-FRONT OPTIMIZED)
Author: Dm.Andreyanov
Organization: Prizolov Market / Prizolov Lab
============================================ -->

# Changelog

## [14.18] - 2026-06-08

### Fixed
- Amvera pip build error on `beautifulsoup4`: removed unused dependency (parsers use httpx + selectolax).
- Added `amvera.yml` duplicate, `ca-certificates` in Dockerfile, explicit PyPI index URL.
- `backend/static/.gitkeep` so Docker COPY succeeds on fresh clone.

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
