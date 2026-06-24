# Phase 3 — Content Delivery & API Key Reveal — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Gate downloadable content + the candidate's Anthropic API key behind the unlock rule (active + booked + now≥unlock_at); stream files efficiently; let the admin paste an (encrypted-at-rest) API key; audit every download and key reveal.

**Architecture:** A single gating helper (`content_access.is_unlocked` / a FastAPI dependency `require_unlocked`) is the one place the active+booked+unlocked rule is enforced. A config-driven `content_manifest` lists the served files (placeholders in `backend/content/`). A `content` router serves a gated file list + streamed downloads (`FileResponse`, which streams from disk — never loads the 150k-row Excel into memory). API-key paste (admin) encrypts via the existing Fernet helper; key reveal (candidate) is unlock-gated, decrypts server-side, and is audited. The frontend candidate dashboard's unlocked state shows the download area + the API key with the required usage note; the admin candidate view gets a paste-key field.

**Tech Stack:** Same as Phases 1–2. No new dependencies (FileResponse is in Starlette).

## Global Constraints

- **Content + API key are gated identically (spec §6 Phase 3):** downloadable/revealable ONLY when the candidate is `active`, has a booking, AND `now >= booking.unlock_at`. Otherwise 403 (countdown shown client-side). This rule lives in ONE helper.
- **API key is a credential (spec §3.3):** stored Fernet-encrypted at rest; revealed only to the authenticated owning candidate over HTTPS; NEVER written to logs or audit detail. The audit row for a reveal records that a reveal happened, not the key.
- **Stream large files (spec §6 Phase 3):** use `FileResponse` (disk streaming); do not read entire files into memory.
- **Files live on the server filesystem** in a `content/` dir (config `CONTENT_DIR`, default `backend/content/`); the manifest maps `file_key → {filename, label, category, media_type}`. Admin replaces files without redeploy. Placeholders ship in the repo's `content/` (gitignored except `.gitkeep`/manifest).
- **Audit every download (`file_download`) and every key reveal (`api_key_reveal`)** via `record(...)`, plus a `download_event` row per download. No secrets in any audit/log.
- Admin pastes the key in the admin candidate view; it is encrypted on save (`api_key_set` audited — no key material).
- Minimal-data rule unchanged; tests run from `backend/` with the 5433 test DB; pristine + ruff clean.

---

## File Structure (Phase 3)

| File | Responsibility |
|------|----------------|
| `backend/app/content_manifest.py` | the served-file manifest + path resolution under CONTENT_DIR |
| `backend/app/content_access.py` | `is_unlocked(db, candidate) -> bool` + `require_unlocked` dependency (403 if locked) |
| `backend/app/config.py` (extend) | `content_dir: str` setting |
| `backend/app/routers/content.py` | gated file list + streamed download |
| `backend/app/routers/candidate_key.py` | candidate gated key reveal |
| `backend/app/routers/admin.py` (extend) | admin paste/clear API key |
| `backend/app/main.py` (extend) | mount new routers |
| `backend/content/` | placeholder files + `MANIFEST` note |
| `backend/tests/test_content.py` | gating, listing, streamed download, download_event, audit |
| `backend/tests/test_apikey.py` | paste(encrypt), reveal(gated, decrypt, audit), no-leak |
| `frontend/src/pages/CandidateDashboard.tsx` (extend) | unlocked: download area + API key reveal + note |
| `frontend/src/pages/AdminDashboard.tsx` (extend) | per-candidate paste-API-key field |

---

## Task 1: Content manifest + unlock gating helper

**Files:** Create `backend/app/content_manifest.py`, `backend/app/content_access.py`; extend `backend/app/config.py`; create `backend/tests/test_content_access.py`; add placeholder files under `backend/content/`.

**Interfaces:**
- `content_manifest.MANIFEST: list[dict]` each `{file_key, filename, label, category, media_type}`. Categories: `brief`, `data`, `reference`.
- `content_manifest.get_entry(file_key) -> dict | None`; `content_manifest.resolve_path(file_key, content_dir) -> Path | None` (returns the path only if the file exists; guards against path traversal — file_key must match a manifest entry, never user-joined).
- `content_access.is_unlocked(db, candidate) -> bool` = candidate.status == "active" AND a booking exists AND `datetime.now(UTC) >= booking.unlock_at`.
- `content_access.require_unlocked` — FastAPI dependency that resolves `current_candidate`, raises 403 "content is locked" if `not is_unlocked`, else returns the candidate.
- `config.Settings.content_dir: str = "content"` (relative to backend working dir).

- [ ] **Step 1: Write failing tests** `test_content_access.py`: `is_unlocked` false when no booking; false when booked but unlock_at in the future; false when status != active; true when active + booked + unlock_at in the past. `resolve_path` returns None for an unknown file_key and rejects a traversal-style key; returns a path for a manifest key whose placeholder file exists.
- [ ] **Step 2: RED.**
- [ ] **Step 3: Implement.** Manifest with ~6 placeholder entries (1 brief, 3 data incl. a `wind_data` xlsx, 2 reference). Create matching small placeholder files in `backend/content/` (real files are admin-supplied later; document in a `backend/content/MANIFEST.md`). `resolve_path` only ever maps a known `file_key` to `content_dir/filename` — never joins arbitrary input.
- [ ] **Step 4: GREEN** + ruff clean.
- [ ] **Step 5: Commit** `feat(backend): content manifest and unlock gating helper`.

---

## Task 2: Gated content list + streamed download

**Files:** Create `backend/app/routers/content.py`; extend `main.py`; create `backend/tests/test_content.py`.

**Interfaces:**
- GET `/api/content` (candidate, unlock-gated via `require_unlocked`) → list of `{file_key, label, category}` from the manifest (only entries whose file exists). 403 if locked.
- GET `/api/content/{file_key}` (candidate, gated) → `FileResponse(path, filename=manifest.filename, media_type=manifest.media_type)` streamed; 404 if file_key unknown/missing; 403 if locked. On success: write a `download_event(candidate_id, file_key)` row and audit `file_download` (detail = file_key, no secrets).

- [ ] **Step 1: Failing tests.** Helper to make a candidate unlocked (book a slot whose unlock is immediate — e.g. a slot 1 hour out so unlock_at == now). Cases: locked candidate (no booking, or future unlock) → 403 on both list and download; unlocked candidate → list returns manifest entries; download returns 200 with the file bytes (assert the response content matches the placeholder file) and the correct `Content-Disposition` filename; a `download_event` row and an `file_download` audit row are written; unknown file_key → 404.
- [ ] **Step 2: RED.**
- [ ] **Step 3: Implement** using `FileResponse`. Record download_event + audit AFTER confirming the file resolves (so a 404 doesn't log a download). Gate with `require_unlocked`.
- [ ] **Step 4: GREEN** + ruff clean + full suite.
- [ ] **Step 5: Commit** `feat(backend): gated streamed content downloads with audit`.

---

## Task 3: Admin paste API key + candidate gated key reveal

**Files:** Extend `backend/app/routers/admin.py`; create `backend/app/routers/candidate_key.py`; extend `main.py`, `schemas.py`; create `backend/tests/test_apikey.py`.

**Interfaces:**
- `ApiKeyPaste{ api_key: str }`.
- PUT `/api/admin/candidates/{candidate_id}/api-key` (admin) → encrypts via `encrypt_secret` and stores in `candidate.api_key_encrypted`; audit `api_key_set` (detail = candidate_id only, NEVER the key). Returns `{ok: true}`. A DELETE on the same path clears it (audit `api_key_clear`), optional.
- GET `/api/me/api-key` (candidate, unlock-gated) → if no key set → 404 "no API key assigned yet"; else decrypt via `decrypt_secret` and return `{api_key, note}` where `note` is the §6 usage message ("this key is for the LLM features your app uses at runtime; it has a fixed budget; track your own spend from token usage in API responses."). Audit `api_key_reveal` (detail = candidate_id only, NEVER the key). 403 if locked.

- [ ] **Step 1: Failing tests `test_apikey.py`.** admin pastes a key → stored value is encrypted (DB column != plaintext) and decrypts back to the original; reveal by a LOCKED candidate → 403; reveal by an UNLOCKED candidate with a key → 200 returns the original key + note, and an `api_key_reveal` audit row exists; reveal with no key set → 404; **no audit row anywhere contains the key string** (assert the plaintext key is absent from all audit details); admin-paste is admin-only (401 otherwise).
- [ ] **Step 2: RED.**
- [ ] **Step 3: Implement.** Reuse `app.security.encrypt_secret/decrypt_secret`. Gate reveal with `require_unlocked`.
- [ ] **Step 4: GREEN** + ruff clean + full suite.
- [ ] **Step 5: Commit** `feat(backend): admin API-key paste (encrypted) and gated candidate key reveal`.

---

## Task 4: Frontend — unlocked dashboard (downloads + key reveal) + admin paste-key

**Files:** Extend `frontend/src/pages/CandidateDashboard.tsx`, `frontend/src/pages/AdminDashboard.tsx`; reuse `api` client.

- [ ] **Step 1 (candidate unlocked state):** When `/api/me/booking` reports `unlocked: true`, fetch `GET /api/content` and render the download area: grouped by category (brief / data / reference), each file a download link/button hitting `GET /api/content/{file_key}` (use a normal anchor or `window.location`/fetch-to-blob so the browser downloads the streamed file). Below it, an "Your API key" section with a "Reveal API key" button → `GET /api/me/api-key`; on success show the key (in a copyable, masked-by-default field) and the returned usage `note`. Handle 404 (no key yet) gracefully ("your assessor hasn't added a key yet").
- [ ] **Step 2 (admin paste-key):** In the AdminDashboard candidate list, add a per-candidate "Set API key" control (a password-type input + Save) → `PUT /api/admin/candidates/{candidate_id}/api-key {api_key}`. Show success/error inline. Never display the stored key back in the admin UI (write-only).
- [ ] **Step 3:** `npm run build` + `npm run lint` clean. No new deps.
- [ ] **Step 4: Commit** `feat(frontend): unlocked download area, API key reveal, admin key paste`.

---

## Phase 3 Checkpoint
Locked candidate sees a countdown (Phase 2) and gets 403 on content/key; unlocked candidate lists + downloads files (streamed, correct filenames) and reveals their API key with the usage note; admin pastes a key that is encrypted at rest and never logged; every download and reveal is audited; the key never appears in any audit/log. Backend suite + frontend build/lint green.

## Self-Review (against spec §3.3 + §6 Phase 3)
- Gating (active + booked + unlocked) in one helper → Task 1. ✓
- Streamed downloads, no whole-file memory load → Task 2 (FileResponse). ✓
- download_event + file_download audit per download → Task 2. ✓
- Admin paste key, encrypted at rest → Task 3. ✓
- Candidate gated key reveal, decrypted server-side, owner-only, usage note, never logged → Task 3. ✓
- api_key_reveal + api_key_set audited without key material → Task 3. ✓
- Frontend unlocked download area + key reveal + admin paste → Task 4. ✓
