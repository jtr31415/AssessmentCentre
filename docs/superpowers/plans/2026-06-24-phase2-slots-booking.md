# Phase 2 — Slots & Booking — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Admin slot management (create/list-with-status/edit/delete-unbooked, delete-protection + reassign/release of booked slots), candidate booking with the §5 prep-window preview, and atomic single-occupancy reservation — all audit-logged.

**Architecture:** A pure `prep_window` module computes `unlock_at` and the human-facing preview (no I/O, exhaustively TDD'd). A `slots` router (admin) and a `booking` router (candidate + admin reassign) sit on top. Booking safety uses `SELECT … FOR UPDATE` on the slot row inside a transaction plus the existing unique constraint on `booking.candidate_id`. Frontend gets an admin slots page and a candidate booking page + booked-state dashboard with a live countdown.

**Tech Stack:** Same as Phase 1 (FastAPI, SQLAlchemy 2.0, Postgres; Vite/React/TS). No new dependencies.

## Global Constraints

- Boring monolith; no new infra/deps. (spec §2, §7)
- `prep_window_days` (N) is read from the `config` table (default 8), NOT hardcoded.
- **Unlock rule (spec §5):** `unlock_at = max(now_at_booking, slot.starts_at − N days)`. Compute `nominal_unlock = slot.starts_at − N days`; if it's already past at booking time, unlock = booking time (immediate). Effective prep = `min(N days, slot.starts_at − booking_time)`.
- `unlock_at` is STORED on the booking row at booking time (stable thereafter); reassignment recomputes it from the new slot and the original `booked_at`.
- A slot is "open" iff `count(bookings) < capacity`. Candidates see ALL open slots (do not hide near slots).
- A candidate has AT MOST ONE booking (DB unique constraint on `booking.candidate_id`, already present).
- Booking must be atomic under concurrency: `SELECT … FOR UPDATE` on the slot row, re-check capacity inside the lock; loser gets HTTP 409 with a clear "that slot was just taken" message.
- A booked slot CANNOT be deleted/edited; admin must reassign the candidate or release the booking first.
- Audit-log every booking, reassignment, and release via the `record(...)` choke-point (no secrets; actor = candidate_id for candidate actions, "admin" for admin actions).
- All datetimes tz-aware UTC; the booking preview formats dates for display using the `display_timezone` config (default Europe/London).
- Tests run from `backend/` with `TEST_DATABASE_URL=postgresql+psycopg://app:app@localhost:5433/app_test` and the repo-root `.venv`. Keep output pristine.

---

## File Structure (Phase 2)

| File | Responsibility |
|------|----------------|
| `backend/app/prep_window.py` | pure unlock_at + preview computation |
| `backend/app/schemas.py` (extend) | SlotCreate, SlotUpdate, BookRequest, ReassignRequest response models |
| `backend/app/routers/slots.py` | admin slot CRUD + status listing |
| `backend/app/routers/booking.py` | candidate open-slot list, preview, book; admin reassign/release |
| `backend/app/main.py` (extend) | mount the two new routers |
| `backend/app/config_helpers.py` | `get_config_int(db, key, default)` / `get_config_str(...)` helpers |
| `backend/tests/test_prep_window.py` | exhaustive prep-window unit tests |
| `backend/tests/test_slots.py` | admin slot CRUD + delete-protection |
| `backend/tests/test_booking.py` | booking, preview, atomicity, one-per-candidate, reassign/release |
| `frontend/src/pages/AdminSlots.tsx` | admin slot management UI |
| `frontend/src/pages/CandidateBooking.tsx` | candidate slot list + preview + confirm |
| `frontend/src/components/Countdown.tsx` | live countdown to unlock_at |
| `frontend/src/pages/CandidateDashboard.tsx` (extend) | booked-state: slot + unlock countdown |
| `frontend/src/App.tsx` (extend) | routes `/admin/slots`, `/book` |

---

## Task 1: `prep_window` pure module + config helpers

**Files:** Create `backend/app/prep_window.py`, `backend/app/config_helpers.py`, `backend/tests/test_prep_window.py`.

**Interfaces:**
- Produces `compute_unlock_at(slot_starts_at: datetime, booked_at: datetime, prep_window_days: int) -> datetime` = `max(booked_at, slot_starts_at - timedelta(days=N))`.
- Produces `build_preview(slot_starts_at, now, prep_window_days, tz_name: str) -> dict` returning `{assessment_at_iso, unlock_at_iso, prep_days: float, assessment_display, unlock_display, unlocks_immediately: bool}` where `prep_days = (slot_starts_at - unlock_at).total_seconds()/86400` rounded to 1 dp, displays formatted in `tz_name` (e.g. "Mon 3 Nov 2026, 14:00").
- Produces `get_config_int(db, key, default)` and `get_config_str(db, key, default)` in config_helpers reading the `config` table.

- [ ] **Step 1: Write failing tests** `test_prep_window.py` covering, with tz-aware UTC datetimes:
  - booking far before slot (e.g. 30 days before, N=8): `unlock_at == slot - 8d`, `prep_days == 8.0`, `unlocks_immediately is False`.
  - booking exactly N days before: unlock == now (immediate), prep_days == 8.0.
  - booking fewer than N days before (e.g. 3 days, N=8): `unlock_at == booked_at` (immediate), `prep_days ≈ 3.0`, `unlocks_immediately is True`.
  - booking 1 hour before slot: unlock immediate, prep_days ≈ 0.04.
  - N read from config default 8; explicit N=5 path.
  - `build_preview` display strings format in Europe/London (assert substring like the weekday + month).
- [ ] **Step 2: Run RED.** `pytest tests/test_prep_window.py -v` → fail (module missing).
- [ ] **Step 3: Implement** `prep_window.py` (use `zoneinfo.ZoneInfo(tz_name)` for display; computation stays in UTC) and `config_helpers.py`.
- [ ] **Step 4: Run GREEN.** All prep-window tests pass, pristine.
- [ ] **Step 5: Commit** `feat(backend): prep-window unlock/preview computation + config helpers`.

---

## Task 2: Admin slot create + list-with-status

**Files:** Extend `backend/app/schemas.py`; create `backend/app/routers/slots.py`; extend `backend/app/main.py`; create `backend/tests/test_slots.py`.

**Interfaces:**
- `SlotCreate{ starts_at: datetime, capacity: int = 1 }`.
- POST `/api/admin/slots` (admin) → 201 `{id, starts_at, capacity, booked_count, is_open}`. Audit `slot_create`.
- GET `/api/admin/slots` (admin) → list of `{id, starts_at, capacity, booked_count, is_open, bookings:[{candidate_id, first_name}]}` ordered by `starts_at`.
- Mount router in `main.py`.

- [ ] **Step 1: Write failing tests** (admin auth via existing helper): create a slot returns 201 with `booked_count==0, is_open==true`; list shows it; non-admin → 401; capacity defaults to 1.
- [ ] **Step 2: RED.**
- [ ] **Step 3: Implement** the endpoints. `booked_count` via a count of bookings for the slot; `is_open = booked_count < capacity`. Join candidate for the `bookings` array (candidate_id + first_name only — no other PII). Audit `slot_create` with detail like `f"slot {id} @ {starts_at} cap {capacity}"`.
- [ ] **Step 4: GREEN.**
- [ ] **Step 5: Commit** `feat(backend): admin slot creation and status listing`.

---

## Task 3: Admin slot edit/delete with booked-protection

**Files:** Extend `slots.py`, `schemas.py`, `test_slots.py`.

**Interfaces:**
- `SlotUpdate{ starts_at: datetime | None, capacity: int | None }`.
- PATCH `/api/admin/slots/{id}` (admin) → updates an UNBOOKED slot; if it has any booking → 409 "slot is booked; reassign or release first". Audit `slot_update`.
- DELETE `/api/admin/slots/{id}` (admin) → deletes an UNBOOKED slot; if booked → 409 (same message). Audit `slot_delete`.

- [ ] **Step 1: Failing tests:** edit/delete unbooked OK; create a booking then edit→409 and delete→409; deleting unknown id → 404.
- [ ] **Step 2: RED.**
- [ ] **Step 3: Implement.** Guard: `if db.query(Booking).filter_by(slot_id=id).first(): raise HTTPException(409, ...)`. (A booking is created in the test via direct insert or the booking endpoint once Task 4/5 exist — for this task insert a Booking row directly in the test.)
- [ ] **Step 4: GREEN.**
- [ ] **Step 5: Commit** `feat(backend): slot edit/delete with booked-slot protection`.

---

## Task 4: Candidate open-slot list + booking preview

**Files:** Create `backend/app/routers/booking.py` (candidate endpoints); extend `main.py`, `schemas.py`, create `backend/tests/test_booking.py`.

**Interfaces:**
- GET `/api/slots/open` (candidate) → list of currently-open slots `{id, starts_at}` ordered by `starts_at` (only `booked_count < capacity`).
- GET `/api/slots/{id}/preview` (candidate) → the §5 preview via `build_preview(slot.starts_at, now, N_from_config, tz_from_config)` → `{assessment_at_iso, unlock_at_iso, prep_days, assessment_display, unlock_display, unlocks_immediately}`. 404 if slot missing.
- Mount router.

- [ ] **Step 1: Failing tests:** open list excludes a full slot (capacity 1 with a booking) and includes an open one; preview returns correct prep_days for a slot 20 days out (N=8 → 8.0) and for a slot 2 days out (→ ~2.0, unlocks_immediately). Candidate auth required (401 otherwise).
- [ ] **Step 2: RED.**
- [ ] **Step 3: Implement** using `prep_window.build_preview` and `config_helpers`. "now" = `datetime.now(UTC)`.
- [ ] **Step 4: GREEN.**
- [ ] **Step 5: Commit** `feat(backend): candidate open-slot list and prep-window preview`.

---

## Task 5: Atomic booking (single occupancy, one-per-candidate)

**Files:** Extend `booking.py`, `test_booking.py`.

**Interfaces:**
- POST `/api/slots/{id}/book` (candidate) → books the slot for the current candidate. On success 201 `{slot_id, unlock_at, booked_at}`; computes & stores `unlock_at` via `compute_unlock_at`. Audit `booking_create` (actor = candidate_id).
- Failure modes: slot full at lock time → 409 "that slot was just taken, please pick another"; candidate already has a booking → 409 "you already have a booking"; slot missing → 404.

- [ ] **Step 1: Failing tests:**
  - happy path: candidate books an open slot → 201; a `booking` row exists with a correct stored `unlock_at`; audit row present.
  - second booking by same candidate (different slot) → 409 "already have a booking" (DB unique also enforces).
  - capacity enforcement: capacity-1 slot, candidate A books, candidate B attempts → 409 "just taken".
  - (concurrency note in the test file comment: real `SELECT FOR UPDATE` race is covered structurally; a 2-thread test is optional and may be flaky in CI — assert the capacity guard logic instead.)
- [ ] **Step 2: RED.**
- [ ] **Step 3: Implement** inside a transaction:
  ```python
  slot = db.execute(select(Slot).where(Slot.id == id).with_for_update()).scalar_one_or_none()
  if not slot: 404
  if db.query(Booking).filter_by(candidate_id=cand.id).first(): 409 already
  count = db.query(Booking).filter_by(slot_id=id).count()
  if count >= slot.capacity: 409 just taken
  unlock_at = compute_unlock_at(slot.starts_at, now, N)
  db.add(Booking(candidate_id=cand.id, slot_id=id, unlock_at=unlock_at, booked_at=now)); db.commit()
  ```
  Handle the unique-violation IntegrityError as a 409 fallback too.
- [ ] **Step 4: GREEN.**
- [ ] **Step 5: Commit** `feat(backend): atomic slot booking with single-occupancy and one-per-candidate`.

---

## Task 6: Admin reassign / release booking

**Files:** Extend `booking.py` (admin endpoints), `schemas.py`, `test_booking.py`.

**Interfaces:**
- `ReassignRequest{ candidate_id: str, new_slot_id: int }`.
- POST `/api/admin/bookings/reassign` (admin) → moves a candidate's booking to a new (open) slot, RECOMPUTES `unlock_at` from the new slot + original `booked_at`. 409 if new slot full; 404 if candidate/booking/slot missing. Audit `booking_reassign`.
- POST `/api/admin/bookings/release` (admin) `{candidate_id}` → deletes the candidate's booking (frees the slot). Audit `booking_release`.

- [ ] **Step 1: Failing tests:** reassign recomputes unlock_at to the new slot's basis; reassign into a full slot → 409; release removes the booking and reopens the slot (open list shows it again); admin-only.
- [ ] **Step 2: RED.**
- [ ] **Step 3: Implement** (lock the new slot with `with_for_update`, capacity check, update booking.slot_id + unlock_at).
- [ ] **Step 4: GREEN.**
- [ ] **Step 5: Commit** `feat(backend): admin booking reassign and release`.

---

## Task 7: Frontend — admin slots management page

**Files:** Create `frontend/src/pages/AdminSlots.tsx`; extend `App.tsx` (route `/admin/slots` + a link from `/admin`).

**Interfaces:** Uses `/api/admin/slots` (GET/POST), PATCH/DELETE `/api/admin/slots/{id}`, and `/api/admin/bookings/{reassign,release}`.

- [ ] **Step 1:** Build the page: a create-slot form (datetime-local + capacity), a table listing slots with status (open / booked-by-`cand-NN`), delete + edit buttons on unbooked slots (disabled/hidden on booked), and a reassign/release control for booked slots. Show server 409 messages inline.
- [ ] **Step 2:** Add the route and a nav link from the admin dashboard.
- [ ] **Step 3:** `npm run build` and `npm run lint` both clean.
- [ ] **Step 4: Commit** `feat(frontend): admin slot management page`.

---

## Task 8: Frontend — candidate booking + booked-state dashboard + countdown

**Files:** Create `frontend/src/pages/CandidateBooking.tsx`, `frontend/src/components/Countdown.tsx`; extend `CandidateDashboard.tsx`, `App.tsx` (route `/book`).

**Interfaces:** Uses `/api/slots/open`, `/api/slots/{id}/preview`, `/api/slots/{id}/book`, and `/api/auth/me` plus a new `/api/me/booking` (add a small candidate endpoint returning the current candidate's booking + unlock_at, or reuse data — see Step 0).

- [ ] **Step 0 (backend tiny add):** GET `/api/me/booking` (candidate) → `{has_booking, slot_starts_at, unlock_at, unlocked: bool}` or `{has_booking:false}`. Add to `booking.py` with a test in `test_booking.py`. Commit can fold into Task 8 or be its own; keep it small.
- [ ] **Step 1:** `CandidateBooking.tsx`: fetch open slots; on selecting a slot, fetch its preview and show the §5 sentence ("If you choose this slot, your data unlocks on **<unlock_display>**, giving you **<prep_days>** days before your assessment on **<assessment_display>**."); a Confirm button calls book; handle 409 by refreshing the list and showing the message.
- [ ] **Step 2:** `Countdown.tsx`: given an `unlockAt` ISO string, render a live H/M/S countdown; when it reaches zero, call an `onUnlock` callback (parent re-fetches `/api/me/booking`). Poll-on-expiry, no manual refresh.
- [ ] **Step 3:** `CandidateDashboard.tsx`: if no booking → link to `/book`; if booked and locked → show assessment time + Countdown to unlock; if booked and unlocked → show "Your data is unlocked" placeholder (the actual download area arrives in Phase 3).
- [ ] **Step 4:** Route `/book`; `npm run build` + `npm run lint` clean.
- [ ] **Step 5: Commit** `feat(frontend): candidate booking, preview, and unlock countdown`.

---

## Phase 2 Checkpoint

Demonstrate locally: admin creates slots; candidate sees open slots with an accurate prep-window preview before confirming; booking is atomic (full slot → clear 409); a candidate can hold at most one booking; booked slots are delete/edit-protected; admin can reassign (unlock_at recomputed) and release; after booking the candidate dashboard shows a live countdown to unlock; bookings/reassignments/releases are audit-logged. Backend suite + frontend build/lint green.

---

## Self-Review (against spec §5 + §6 Phase 2)
- Admin slot create/list-with-status/edit/delete → Tasks 2,3. ✓
- Booked-slot delete-protection + reassign/release (unlock recompute) → Tasks 3,6. ✓
- Candidate open-slot list (no near-slot hiding) + prep-window preview → Task 4. ✓
- Atomic SELECT FOR UPDATE booking, one-per-candidate, graceful 409 → Task 5. ✓
- unlock_at = max(now, slot − N), stored on booking, effective prep = min(N, gap) → Tasks 1,5. ✓
- After-booking live countdown that self-reveals (download area itself is Phase 3) → Task 8. ✓
- Audit bookings + reassignments → Tasks 5,6. ✓
