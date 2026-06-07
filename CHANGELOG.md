<!-- ============================================
Copyright (c) 2026
PRIZOLOV SPORTS AI v14.0 (STORE-FRONT OPTIMIZED)
Author: Dm.Andreyanov
Organization: Prizolov Market / Prizolov Lab
============================================ -->

# Changelog

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
