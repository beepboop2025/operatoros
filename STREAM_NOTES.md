# Stream Notes — Phase 3 (CI, Docker, config, dev ergonomics)

## Items completed
- Added `REDIS_PASSWORD` support to `backend/app/config.py` (injected into `REDIS_URL`,
  `CELERY_BROKER_URL`, and `CELERY_RESULT_BACKEND`).
- Added startup validation that fails fast when no LLM provider is usable
  (`FREE_LLM_ENABLED=false` and `OPENROUTER_API_KEY` empty).
- Created `backend/requirements-dev.txt` with pytest/pytest-asyncio/pytest-cov/httpx/ruff/mypy.
- Created `.github/workflows/ci.yml` with backend (import-check + pytest) and frontend
  (typecheck/lint/build) jobs, including Postgres + Redis service containers.
- Created root `Makefile` with `test`, `lint`, `migrate`, `seed`, `up`, `down`, `build`.
- Added frontend service to `docker-compose.yml` (development target, Vite dev server,
  hot-reload volume, `VITE_API_URL=http://fastapi:8000`, `depends_on: fastapi`).
- Added frontend service to `docker-compose.prod.yml` (production Nginx target) and
  updated Caddyfile to reverse-proxy `app.{$DOMAIN}` to `frontend:80`.
- Updated `frontend/Dockerfile` with a `development` stage and `frontend/nginx.conf` to
  proxy `/api/*` to the FastAPI backend.
- Updated `frontend/vite.config.ts` to use `VITE_API_URL` for the dev proxy target.
- Added `frontend/eslint.config.js` and missing ESLint/TS dependencies so `npm run lint`
  works under ESLint v9.
- Created `.env.prod.example` with required production variables and `SECRET_KEY`
  generation note.
- Added minimal `backend/tests/conftest.py` and `backend/tests/test_config.py` so the
  `pytest -q` CI step has passing tests for the new config behaviour.

## Pre-existing blockers fixed to make the Phase 3 gate pass
These were not originally in the Phase 3 scope, but they prevented `python -c "import app.main"`
from succeeding, which the acceptance gate requires:
- `backend/app/routes/compliance.py`: moved the parameter without a default
  (`request: Request`) before parameters with `Query(...)` defaults to fix a `SyntaxError`.
- `backend/app/routes/dashboard.py`: aliased `from app.models.query import Query` to
  `QueryModel` because it shadowed FastAPI's `Query`, causing a `TypeError` at import time.

## Could not run
- `docker compose config` / `docker compose -f docker-compose.prod.yml config` could not
  be executed because Docker is not installed in this environment. The YAML syntax of both
  files was validated with Python (`yaml.safe_load`). The compose files should be run
  through `docker compose config` on a machine with Docker before the gate is considered
  fully closed.
