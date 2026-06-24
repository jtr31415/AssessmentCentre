# Phase 4 — Q&A & Admin Area — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Private per-candidate Q&A (candidate asks, human admin answers); an admin question queue; admin account management (reset password, re-issue invite, disable/enable); and an admin activity/monitoring view — all audit-logged.

**Architecture:** A `qa` router holds candidate (own questions only) and admin (all questions) endpoints; privacy is enforced by always scoping candidate reads/writes to the session candidate. Admin account actions extend the existing `admin` router and reuse the Phase 1 token/seed machinery. The activity view is a read-only aggregator over `candidate`, `booking`, `download_event`, and `audit_log`. Frontend adds a candidate Q&A page and admin pages for the queue, account management, and the activity table.

**Tech Stack:** Same as Phases 1–3. No new dependencies.

## Global Constraints

- **Q&A is strictly private per candidate (spec §7):** a candidate can only ever read/append their OWN questions; no shared board; no candidate sees another's questions or answers. Enforced by scoping every candidate query to `session candidate.id` — never a path/body candidate id.
- **Human-answered, not a chatbot:** the candidate UI shows an expectation line using the admin-set `qa_sla_text` config value.
- **Admin-only** for the queue, answering, account management, and activity view (via `current_admin`).
- **Audit (spec §3.6):** `question_submit`, `question_answer`, `password_reset`, `invite_reissue`, `account_disable`, `account_enable` — all via `record(...)`, no secrets (never the token, never answer/question bodies beyond an id reference; detail = ids only).
- **Minimal data** unchanged. The activity view exposes only candidate_id + first_name + derived status/event facts (no PII beyond first name).
- Reset/re-issue produce a NEW one-time set-password token (single-use, expiring) shown to the admin to send manually — the app never emails.
- Disable sets `status="disabled"` (login already rejects non-active); re-enable restores `status="active"` (only if the candidate has a password set, else `invited`).
- Tests run from `backend/` with the 5433 test DB and the SHARED conftest `db_session`/`client` fixtures (do NOT define a local engine fixture — it drops the shared schema). Pristine + ruff clean.

---

## File Structure (Phase 4)

| File | Responsibility |
|------|----------------|
| `backend/app/routers/qa.py` | candidate submit/list own; admin queue/answer |
| `backend/app/routers/admin.py` (extend) | reset password, re-issue invite, disable/enable, activity view |
| `backend/app/schemas.py` (extend) | QuestionCreate, AnswerCreate |
| `backend/app/main.py` (extend) | mount qa router |
| `backend/tests/test_qa.py` | submit/list/privacy/answer/audit |
| `backend/tests/test_admin_accounts.py` | reset/reissue/disable/enable + login effects + audit |
| `backend/tests/test_activity.py` | activity aggregation correctness |
| `frontend/src/pages/CandidateQA.tsx` | candidate ask + own thread + SLA note |
| `frontend/src/pages/AdminQuestions.tsx` | admin queue + answer |
| `frontend/src/pages/AdminActivity.tsx` | activity table |
| `frontend/src/pages/AdminDashboard.tsx` (extend) | account-management controls + nav links |
| `frontend/src/App.tsx` (extend) | routes `/questions`, `/admin/questions`, `/admin/activity` |

---

## Task 1: Q&A backend (candidate private + admin queue)

**Files:** Create `backend/app/routers/qa.py`; extend `schemas.py`, `main.py`; create `backend/tests/test_qa.py`.

**Interfaces:**
- `QuestionCreate{ body: str }`; `AnswerCreate{ answer: str }`.
- POST `/api/me/questions` (candidate) → creates a `Question(candidate_id=cand.id, body)`; audit `question_submit` (detail = question id only). 201 `{id, body, asked_at, answer, answered_at}`. Reject empty body (422/400).
- GET `/api/me/questions` (candidate) → the SESSION candidate's questions only, newest first, each `{id, body, asked_at, answer, answered_at}`. Plus `{sla_text}` available via a small GET `/api/me/qa-meta` OR include the SLA in this response envelope — return `{questions:[...], sla_text}`.
- GET `/api/admin/questions` (admin) → ALL questions with asker: `{id, candidate_id, first_name, body, asked_at, answer, answered_at, answered: bool}`, unanswered first (or flagged), newest within group.
- POST `/api/admin/questions/{id}/answer` (admin) → sets `answer`, `answered_at=now`; audit `question_answer` (detail = question id). 404 if missing.

- [ ] **Step 1: Failing tests** (`test_qa.py`, shared fixtures, candidate-flow helpers): candidate submits → appears in their own list with null answer; **privacy: candidate B does NOT see candidate A's question** (B's list excludes A's); admin sees both with asker ids; admin answers one → it shows the answer in that candidate's list and is flagged answered in the admin queue; empty body rejected; candidate cannot hit the admin endpoints (401); `sla_text` returned.
- [ ] **Step 2: RED.**
- [ ] **Step 3: Implement** `qa.py`. SLA from `get_config_str(db,"qa_sla_text", <default>)`. All candidate queries filter by `cand.id`.
- [ ] **Step 4: GREEN** + ruff clean + full suite.
- [ ] **Step 5: Commit** `feat(backend): private candidate Q&A with admin queue and answers`.

---

## Task 2: Admin account management (reset / re-issue / disable / enable)

**Files:** Extend `backend/app/routers/admin.py`, `schemas.py`; create `backend/tests/test_admin_accounts.py`.

**Interfaces:** (all admin-only; candidate looked up by `candidate_id` string; 404 if missing)
- POST `/api/admin/candidates/{candidate_id}/reset-password` → generate a NEW one-time token (24h expiry), set it on the candidate, set `status` appropriately (password reset means they must set again — keep `status` but clear `password_hash`? Decision: KEEP existing password valid until they use the new link is risky; instead set a fresh token WITHOUT clearing the current password — the link lets them set a new one, consuming the token. On set-password the existing flow sets password + status active). Return `{set_password_path}`. Audit `password_reset` (candidate_id only, never the token).
- POST `/api/admin/candidates/{candidate_id}/reissue-invite` → for an `invited` candidate, regenerate the one-time token + expiry; return `{set_password_path}`. Audit `invite_reissue`.
  - (reset-password and reissue-invite are nearly identical; share a helper that mints a token and returns the path. Keep both endpoints for clear admin intent.)
- POST `/api/admin/candidates/{candidate_id}/disable` → `status="disabled"`; audit `account_disable`. Return `{status}`.
- POST `/api/admin/candidates/{candidate_id}/enable` → `status = "active" if password_hash else "invited"`; audit `account_enable`. Return `{status}`.

- [ ] **Step 1: Failing tests:** reset-password returns a new token path and a DIFFERENT token than any prior; using the new token via the existing set-password flow works; disable → candidate login now 401 even with correct password; enable restores login (active) for a candidate with a password; enable of a never-set candidate yields `invited`; re-issue for an invited candidate gives a fresh working token; admin-only; the token never appears in any audit detail.
- [ ] **Step 2: RED.**
- [ ] **Step 3: Implement** (reuse `generate_token`, the `_set_password_path` helper from Phase 1). 
- [ ] **Step 4: GREEN** + ruff clean + full suite.
- [ ] **Step 5: Commit** `feat(backend): admin account management (reset/reissue/disable/enable)`.

---

## Task 3: Admin activity / monitoring view

**Files:** Extend `backend/app/routers/admin.py`; create `backend/tests/test_activity.py`.

**Interfaces:**
- GET `/api/admin/activity` (admin) → list, one row per candidate, ordered by candidate_id:
  `{candidate_id, first_name, status, has_booking, slot_starts_at|null, unlock_at|null, has_logged_in: bool, downloads: {file_key: downloaded_at|null for each manifest file}, key_revealed: bool, question_count: int}`.
  - `has_logged_in` = exists an `audit_log` row with `actor==candidate_id and action=="login"`.
  - `downloads` derived from `download_event` rows for the candidate (latest per file_key); include every manifest file_key with null if never downloaded.
  - `key_revealed` = exists an `audit_log` row `action=="api_key_reveal"` for the candidate, OR `candidate.api_key_encrypted is not None` is NOT it — use the audit (whether they actually revealed). Use audit `api_key_reveal`.
  - `question_count` = count of questions for the candidate.

- [ ] **Step 1: Failing tests:** seed a candidate with a booking, a login audit row, a download_event for one file, a reveal audit row, and 2 questions; assert the activity row reflects all of it (has_booking true, unlock_at set, has_logged_in true, that file's downloaded_at set + others null, key_revealed true, question_count 2). A fresh `invited` candidate shows all-false/empty. Admin-only.
- [ ] **Step 2: RED.**
- [ ] **Step 3: Implement** as a read aggregator. Keep it simple (per-candidate queries are fine at ~15 candidates). Reuse `content_manifest.MANIFEST` for the file_key set.
- [ ] **Step 4: GREEN** + ruff clean + full suite.
- [ ] **Step 5: Commit** `feat(backend): admin activity/monitoring view`.

---

## Task 4: Frontend — candidate Q&A page

**Files:** Create `frontend/src/pages/CandidateQA.tsx`; extend `App.tsx` (route `/questions`) + a link from the candidate dashboard.

- [ ] **Step 1:** `CandidateQA.tsx`: a textarea + Submit → `POST /api/me/questions`; below it, the candidate's own thread from `GET /api/me/questions` (each question with its answer or an "Awaiting answer" badge). Show the `sla_text` expectation line prominently ("Questions are answered by a person…"). On submit success, clear the box and refresh the list.
- [ ] **Step 2:** Route `/questions`; link from `CandidateDashboard` ("Ask the assessor a question").
- [ ] **Step 3:** `npm run build` + `npm run lint` clean.
- [ ] **Step 4: Commit** `feat(frontend): candidate Q&A page`.

---

## Task 5: Frontend — admin questions queue + account management + activity view

**Files:** Create `frontend/src/pages/AdminQuestions.tsx`, `frontend/src/pages/AdminActivity.tsx`; extend `AdminDashboard.tsx`, `App.tsx` (routes `/admin/questions`, `/admin/activity`).

- [ ] **Step 1 (questions queue):** `AdminQuestions.tsx`: `GET /api/admin/questions`; show unanswered first with a clear "Unanswered" flag; each row shows the asker (`candidate_id` + first_name), the question, and an answer textarea + Save → `POST /api/admin/questions/{id}/answer`; refresh on save.
- [ ] **Step 2 (account management):** in `AdminDashboard.tsx` candidate rows, add controls: Reset password (`POST .../reset-password` → show the returned set-password link to copy), Re-issue invite (for invited), Disable/Enable (toggle by status). Show returned links/status inline.
- [ ] **Step 3 (activity view):** `AdminActivity.tsx`: `GET /api/admin/activity` → a table: candidate, status, booked slot/unlock, logged-in?, per-file downloaded?, key revealed?, #questions. Read-only.
- [ ] **Step 4:** routes `/admin/questions` + `/admin/activity` + nav links from `/admin`.
- [ ] **Step 5:** `npm run build` + `npm run lint` clean.
- [ ] **Step 6: Commit** `feat(frontend): admin questions queue, account management, activity view`.

---

## Phase 4 Checkpoint
Candidate asks a question and sees only their own thread + the SLA note; admin sees all questions with askers, answers from the queue, and the answer appears privately to that candidate; admin can reset/re-issue/disable/enable accounts (with login effects) and view the activity overview; everything audit-logged with no secrets. Backend suite + frontend build/lint green.

## Self-Review (against spec §6 Phase 4 + §7)
- Candidate private Q&A (own only, no cross-candidate) → Task 1 (privacy test). ✓
- Human-answered expectation/SLA wording → Tasks 1 + 4. ✓
- Admin queue with asker + answer + unanswered flag → Tasks 1 + 5. ✓
- Admin account management (reset/reissue/disable/enable) → Tasks 2 + 5. ✓
- Admin activity view (status, slot, unlock, login, downloads, key reveal, question count) → Tasks 3 + 5. ✓
- Audit questions + answers + account actions → Tasks 1, 2. ✓
