# Phase 2 — Stream Notes

## Scope
Completed the Phase 2 items from `KIMI_TASKS.md`:

1. Wired `draft.py` endpoints (`/response`, `/advisory`, `/engagement-letter`) to
   `CommunicationDrafter`.
2. Wired `notices.py` `/{notice_id}/draft-response` to
   `CommunicationDrafter.draft_notice_response()`.
3. Implemented `smart_order()` in `free_llm_router/policy.py`.
4. Removed dashboard hardcodes:
   - `compliance-calendar` now derives `entity_type` from active clients.
   - Removed `revenue_this_month` from `DashboardStats` and the frontend
     `DashboardStats` interface (it was not displayed in the UI and only showed
     a misleading ₹0).
5. Tightened `queries.py` fallback: logs with context, sets `model_used =
   "unavailable"`, and exposes `fallback: bool` in `QueryResponse`.
6. Added pytest infrastructure (`backend/pyproject.toml`,
   `backend/requirements-dev.txt`) and tests for `smart_order` and the draft
   wiring.

## Out-of-scope fixes required for the acceptance gate
Two pre-existing issues blocked `python -c "import app.main"` and were fixed
with minimal changes:

- `backend/app/routes/compliance.py`: `generate_calendar` had `request: Request`
  after query parameters with defaults, causing a Python syntax error. Moved
  `request` to the first parameter position.
- `backend/app/routes/dashboard.py`: `Query` from `app.models.query` shadowed
  FastAPI's `Query`, causing `TypeError` in the compliance-calendar route.
  Renamed the model import to `QueryModel`.

## Frontend verification
- `npm run typecheck` and `npm run build` pass.
- `npm run lint` fails because the repo lacks an ESLint v9 config file
  (`eslint.config.js`). This is pre-existing and unrelated to Phase 2 changes.

## Acceptance gate results
- `python -c "import app.main"` — clean.
- `python3 -m pytest -q` — 14 passed.
