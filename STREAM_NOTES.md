# STREAM_NOTES.md — Phase 4 backend gaps

These are endpoints/functionality the frontend now expects but that do not exist in the backend (`backend/app/routes/*`) as of this commit. They are listed here because Phase 4 is frontend-only and the backend routes were not modified.

1. **Auth token refresh**
   - Expected: `POST /api/auth/refresh` returning a new `access_token`.
   - Status: Not implemented.
   - Frontend behavior: `api/client.ts` attempts silent refresh on HTTP 401 and falls back to logout when the endpoint is missing/returns 404.

2. **Notice response submission**
   - Expected: `POST /api/notices/{id}/submit-response` to persist/file the edited response.
   - Status: Not implemented. The closest existing route is `PUT /notices/{id}` (status/deadline/summary/assignee only).
   - Frontend behavior: `NoticeManager.tsx` exposes a "Submit Response" button that calls the intended endpoint. It will fail until the backend adds it.

3. **Document download / file serving**
   - Expected: `GET /api/documents/{id}/download` returning the original file blob.
   - Status: Not implemented. `DocumentResponse` also does not expose `file_url` or `original_filename` consistently, so the UI cannot construct an alternative download URL.
   - Frontend behavior: `DocumentManager.tsx` shows a "Download File" button that calls the intended endpoint. It will fail until the backend adds it.

4. **Notifications endpoint**
   - Expected: e.g. `GET /api/notifications/unread` (or similar) to drive the notification bell unread indicator.
   - Status: Not implemented.
   - Frontend behavior: The hardcoded red dot on the bell in `Layout.tsx` was removed so it is not misleading.

5. **Notice response fields in API contract (schema gap)**
   - `NoticeResponse` does not expose `response_draft`, `filed_response`, `section`, `assessment_year`, `din`, `title`, `issues`, etc. The frontend interface includes these fields, but the list/detail endpoints only return `description` (mapped from `summary`), `notice_type`, `issue_date`, `response_deadline`, and status.
   - As a result, existing drafts shown in the notice detail modal rely on the separate `draft-response` endpoint rather than the list/detail payload.

---

# Phase 7 — NRI cross-border taxation modules (backend engines)

The backend engines, schemas, routes and unit tests for Phase 7 are implemented
in `backend/app/services/nri_engine.py`, `backend/app/schemas/nri.py` and
`backend/app/routes/nri.py`.  The items below are **blocked pending authoritative
data sourcing / CA review** and are committed as-is.

1. **DTAA treaty withholding rates**
   - Status: Explorer returns metadata + tie-breaker + documentation requirements.
   - Blocked: Actual dividend/interest/royalty/FTS/capital-gains rates for
     USA/UAE/UK/Canada/Australia/Singapore are not yet sourced.
   - See: `backend/DTAA_TODO.md`.

2. **Section 195 domestic TDS rates**
   - Status: Engine computes TDS when `domestic_rate_override` or
     `treaty_rate_override` is supplied.
   - Blocked: Finance Act 2025/2026 First Schedule Section 195 rates are not
     hard-coded; missing rates return `applicable_rate: null`.
   - See: `backend/DTAA_TODO.md` / `backend/TARIFF_TODO.md`.

3. **Customs tariff rates**
   - Status: Import-duty calculator computes BCD + SWS + cess + IGST when all
     rates are provided as overrides.
   - Blocked: `_CUSTOMS_TARIFF_RATES` is empty; HSN-keyed BCD/IGST/cess rates
     and FTA preferential rates require CHA/CA sourcing.
   - See: `backend/TARIFF_TODO.md`.

4. **Residential-status AY 2026-27 thresholds**
   - Status: Engine uses the documented `₹15L → 120-day` visitor rule for
     AY 2026-27 and later, and `182-day` for earlier AYs.
   - Blocked: Final Finance Act 2026 / Income-tax Act 2025 rule text should be
     verified against the gazetted law before relying on the 120-day value.
