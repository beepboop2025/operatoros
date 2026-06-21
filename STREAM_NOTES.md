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

## Phase 6 — blocked / out-of-scope items

Phase 6 was a frontend-only reskin (Textura design system + landing + dashboard reskin). The backend gaps above were **not** addressed in this phase and remain blocked for a subsequent backend pass. No tax rates, treaty values, thresholds, or customs duties were invented in this phase.
