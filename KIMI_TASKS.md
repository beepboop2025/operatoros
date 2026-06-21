# OperatorOS — Completion Brief (for Kimi Code)

Repo: `/Users/mrinal/operatoros`. A CA / tax-advisory platform:
**FastAPI + SQLAlchemy async + pgvector + Redis + Celery + free-llm-router** backend,
**React 18 + Vite 5 + TanStack Query + TS (strict)** frontend, Docker Compose + n8n.

The app is ~80% complete and architecturally sound. This brief lists the remaining work
to get it to "completely finished," in execution order. Each phase has a hard acceptance
gate. **Do not mark a task done until its gate passes and you paste the command output.**

---

## Ground rules (read first)

1. **Backend**: work inside `backend/`. Use the existing venv/requirements pattern; add
   test deps to `requirements.txt` (or a new `requirements-dev.txt`).
2. **Frontend**: work inside `frontend/`. Use **npm** (there's a `package.json` with
   `lint`/`typecheck`/`build` scripts). Match the existing component/style patterns.
3. **Do not invent tax law or legal content.** For anything involving Indian tax rules
   (slabs, TDS rates, CII, GST rates, section numbers), use ONLY values already present in
   `backend/app/services/tax_engine.py` and `backend/app/knowledge/`. If you need a value
   that isn't there, STOP and list it as an open question — do not guess.
4. **Never weaken a test to make it pass.** If a tax test you wrote disagrees with the
   engine's output, that is a *finding to report*, not a test to "fix" by copying the
   engine's number. See Phase 1 guardrail.
5. **Preserve API contracts.** When wiring stubs to real services (Phase 2), the JSON
   response shape returned to the frontend must not change — only the *content* becomes
   real instead of hardcoded.
6. **Secrets**: never commit real keys. `.env.example` only.
7. **Acceptance gate per phase** (run from the relevant dir):
   - Backend: `pytest -q` (+ the phase-specific command) and `python -c "import app.main"`
     must succeed.
   - Frontend: `npm run typecheck && npm run lint && npm run build` must pass.

---

## PHASE 1 — Test infrastructure + tax-engine unit tests  ⭐ highest value

**Why first:** the tax engine is pure, deterministic, Decimal-based, and the financial
core of the product. Zero tests exist anywhere in the repo.

1. Add dev deps: `pytest`, `pytest-asyncio`, `pytest-cov`, `httpx` (for route tests later).
   Add a `pytest.ini` (or `pyproject.toml` `[tool.pytest.ini_options]`) with
   `asyncio_mode = auto` and `testpaths = backend/tests`.
2. Create `backend/tests/` with `conftest.py` (fixtures for building the request
   dataclasses in `tax_engine.py`).
3. Write unit tests for these PURE functions in
   `backend/app/services/tax_engine.py`:
   - `compute_income_tax` (`:468`) — old vs new regime, 87A rebate, surcharge, marginal
     relief, cess. Cover income points around every slab boundary and surcharge threshold.
   - `_compute_tax_from_slabs` (`:305`), `_apply_marginal_relief` (`:344`),
     `_compute_old_regime_deductions` (`:377`) — the internal helpers.
   - `compute_tds` (`:689`) — PAN vs no-PAN, thresholds, multiple sections.
   - `compute_gst` (`:793`) — intra-state (CGST+SGST) vs inter-state (IGST).
   - `compute_capital_gains` (`:885`) — LTCG/STCG, CII indexation, pre/post-Jul-2024.
   - `compute_interest_234` (`:1117`), `compute_hra_exemption` (`:1299`),
     `compute_depreciation` (`:1365`).
   - Edge cases everywhere: zero, negative, very high income, missing optional fields,
     boundary values.

   **GUARDRAIL (critical):** derive each expected value **from the tax rules in the code +
   first principles**, then assert the engine matches. When you hand-compute a slab/rebate
   case and the engine disagrees, record it in a `PHASE1_FINDINGS.md` as a *suspected
   engine bug* — DO NOT edit the test to echo the engine's output. The point of these tests
   is to catch real calculation bugs, so a test that just mirrors current output is worthless.

**Gate:** `pytest backend/tests -q --cov=app.services.tax_engine` green; coverage report
pasted; `PHASE1_FINDINGS.md` lists any disagreements (empty is fine).

---

## PHASE 2 — Finish stubbed backend logic

These are real, concrete stubs (verified). Each wires existing-but-unused code.

1. **Wire LLM draft endpoints to the real service.** `backend/app/routes/draft.py`
   returns hardcoded boilerplate at `~:103` (`draft_response`) and `~:179`
   (`draft_advisory`). The service `backend/app/services/communication_drafter.py`
   (`CommunicationDrafter`) already implements `draft_advisory`, `draft_notice_response`,
   `draft_engagement_letter`, `draft_email`, `draft_client_circular`. Inject the service
   (follow how other routes obtain the OpenRouter/LLM client) and replace the hardcoded
   strings with real calls. Keep the response schema identical. Handle LLM failure by
   returning a clear 503 (do not silently return the old placeholder).
2. **Same for notices.** `backend/app/routes/notices.py:~337` `draft_notice_response`
   returns a hardcoded template → call `CommunicationDrafter.draft_notice_response()`.
3. **Implement provider ranking.** `backend/free_llm_router/policy.py` `smart_order()`
   (`~:45`, `TODO(you)`) just delegates to static priority. Implement the ranking the
   docstring describes: order providers by (circuit healthy first, then token/quota
   availability, then static priority). Pure function over the stats it's given — easy to
   unit-test; add a test for it.
4. **Remove hardcoded dashboard values** in `backend/app/routes/dashboard.py`:
   - `~:330` compliance calendar is hardcoded to `entity_type="private_limited"` — derive
     entity type from the actual client(s) instead.
   - `~:116` `revenue_this_month` is hardcoded `Decimal("0")` ("no revenue model yet").
     Either compute from a real source if one exists, or remove the field from the
     response and the frontend so the dashboard doesn't show a misleading ₹0. Pick one and
     note which.
5. **Tighten the query fallback.** `backend/app/routes/queries.py` (`~:108`) catches broad
   exceptions and saves a record with `model_used = "placeholder"`. Keep graceful
   degradation but: log with context, and make the failure visible to the caller (a flag
   in the response) rather than returning a fake-looking answer.

**Gate:** `python -c "import app.main"` imports clean; `pytest -q` still green; for each
endpoint, paste a curl/httpx call showing real (non-placeholder) output, or the explicit
503 path.

---

## PHASE 3 — CI, Docker, config, dev ergonomics

1. **CI**: add `.github/workflows/ci.yml` running on push/PR:
   - backend job: install deps, `pip install` dev deps, run `pytest -q`, run `ruff`/`flake8`
     + `mypy` if you add them (optional), import-check `app.main`.
   - frontend job: `npm ci`, `npm run typecheck`, `npm run lint`, `npm run build`.
   Use a Postgres+Redis service container for any tests that need them (the pure tax tests
   don't).
2. **Makefile** at repo root: `test`, `lint`, `migrate`, `seed`, `up` (docker compose up),
   `down`. Map each to the real command.
3. **Frontend in docker-compose.** A `frontend/Dockerfile` and `nginx.conf` already exist,
   but `docker-compose.yml` has no `frontend` service. Add one (build `./frontend`, serve
   on a port, `VITE_API_URL` env, `depends_on: fastapi`). Do the same in
   `docker-compose.prod.yml` (or document that Caddy serves the built `dist`).
4. **Redis password support.** `backend/app/config.py` builds `REDIS_URL` with no password;
   `docker-compose.prod.yml` expects one. Add `REDIS_PASSWORD` support and build the URL
   as `redis://:<pw>@host:6379/0` when set. Apply to the Celery broker URL too.
5. **Startup config validation.** In `config.py`, fail fast (clear error) if no LLM
   provider is usable: i.e. `FREE_LLM_ENABLED` is false AND `OPENROUTER_API_KEY` is empty.
   Keep the existing `SECRET_KEY` placeholder rejection.
6. **`.env.prod.example`**: add one with `CORS_ORIGINS=https://yourdomain`, `DOMAIN`,
   `REDIS_PASSWORD`, `N8N_BASIC_AUTH_PASSWORD`, and a note to generate `SECRET_KEY` via
   `python -c "import secrets; print(secrets.token_hex(32))"`.

**Gate:** CI workflow is valid and each step maps to a passing command; `docker compose
config` validates with the new frontend service; `python -c "import app.config"` works
with and without `REDIS_PASSWORD` set.

---

## PHASE 4 — Finish the frontend

Match existing patterns in `frontend/src` (TanStack Query, the `api/client.ts` layer, the
Toast/Skeleton/ErrorBoundary components). Keep the visual language unchanged.

1. **Auth token refresh.** `hooks/useAuth.tsx` + `api/client.ts` log the user out on 401
   with no refresh attempt. Implement silent refresh against the refresh-token endpoint
   (if the backend exposes one — verify in `routes/auth.py`; if not, note it as a backend
   gap) before falling back to logout.
2. **Notice draft is sent empty.** `components/NoticeManager.tsx:~58` calls
   `draftMutation.mutate({ id, data: {} })`. After Phase 2 makes drafting real, add a small
   modal/textarea so the user can review/edit the generated draft, and a submit path. If a
   "submit response" endpoint doesn't exist, list it as a backend gap.
3. **Client edit.** `api/client.ts` has a client-update call that's never used and
   `ClientDetail.tsx` is read-only. Add an edit modal wired to the update endpoint.
4. **Document download.** `DocumentManager.tsx` shows document details but has no download.
   Add a download button if/when a file-serving endpoint exists (verify
   `routes/documents.py`; note as backend gap if missing).
5. **Notification bell.** `Layout.tsx:~167` shows a hardcoded red dot with no data source.
   Either wire it to a notifications endpoint (verify it exists; note if not) or remove the
   dot so it isn't misleading.
6. **Error typing.** Many components repeat `err as { response?: { data?: { detail?: string
   } } }`. Add one shared `ApiError` type in `api/client.ts` and a helper
   `getErrorMessage(err)`, then use it everywhere those casts appear.
7. **Dead code**: remove the unused-import eslint-disable in `ClientDetail.tsx`, and either
   use or delete `formatCurrencyShort` in `utils/format.ts` and the duplicate local
   `SkeletonCard` in `Dashboard.tsx` (import from `Skeleton.tsx`).

**Gate:** `npm run typecheck && npm run lint && npm run build` all pass; list every
"backend gap" you discovered (endpoints the UI needs that don't exist).

---

## PHASE 5 — Knowledge base expansion  ⚠️ needs human review

`backend/app/knowledge/tax_sections.py` covers Income-Tax sections and some GST circulars
but is missing TDS section detail and others. **Expanding legal content is risky for an
automated agent** — wrong section text or rates would silently corrupt RAG answers.

- You MAY scaffold the data structure and add entries **only** for sections/rates that are
  already referenced elsewhere in the codebase (e.g. the TDS sections already encoded in
  `tax_engine.compute_tds`). Mirror those authoritative values.
- For anything not already in the codebase, produce a `KNOWLEDGE_TODO.md` listing exactly
  which sections/circulars are missing — do NOT author legal text from memory.

**Gate:** any added entry traces to an existing in-repo source; `KNOWLEDGE_TODO.md` lists
the rest.

---

## OUT OF SCOPE / do not do unsupervised
- Production observability stack (Sentry/Prometheus/OpenTelemetry) — infra decision, leave
  for the owner.
- Authoring new tax/legal content from outside knowledge (Phase 5 guardrail).
- Any change to `SECRET_KEY` handling beyond what Phase 3 specifies.

## FINAL REPORT
Output, in order:
1. `pytest -q` + coverage summary (backend) and `npm run build` output (frontend).
2. Files added/changed grouped by phase.
3. `PHASE1_FINDINGS.md` (suspected tax bugs), the list of frontend "backend gaps", and
   `KNOWLEDGE_TODO.md`.
4. Anything you could not complete and why.
