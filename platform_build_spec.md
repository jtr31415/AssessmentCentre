# BUILD SPEC — Candidate Assessment Platform

> **For Claude Code.** Build this top to bottom, following the phases in order. Check in at the end of each phase. This is a small, single-purpose internal application for ~15 users. **Favour boring, simple, monolithic solutions.** Do not introduce microservices, message queues, Redis, Kubernetes, or any distributed-systems machinery — none of it is warranted at this scale and it will only add fragility. When in doubt, choose the simpler option and ask.

---

## 1. What this is

A web application that runs a recruitment assessment for a small set of pre-invited candidates. Each candidate logs in, books one of several assessment slots, and — a fixed number of days before their slot — gains access to download an exercise brief, data files, and background reference material. Candidates can ask the assessor private questions through the app, answered only by a human admin. A single admin (the assessor) manages accounts, slots, questions, and content through an admin area.

There is exactly **one admin** (the assessor) and roughly **15 candidates**. Load is trivial; correctness, clarity, and data protection matter far more than performance.

---

## 2. Stack (fixed)

- **Backend:** Python, FastAPI.
- **Frontend:** Vite + React.
- **Database:** PostgreSQL.
- **Reverse proxy / TLS:** Caddy (automatic Let's Encrypt certificates).
- **Deployment:** Docker Compose on a single Hetzner VPS. One container each for backend, frontend (or static build served by Caddy), Postgres, and Caddy.
- **CI:** GitHub Actions — lint, tests, and container build on push.

Do not deviate from this stack. If you believe a deviation is justified, stop and ask first.

---

## 3. Hard rules (security & data protection — non-negotiable)

These override convenience everywhere in the build:

1. **Minimal personal data.** The ONLY personal data stored about a candidate is their **first name**. No email, no surname, no phone. Email invitations are sent manually by the admin outside this system — the app never stores or sends email.
2. **Candidate identity** is a system-generated **candidate ID** (e.g. `cand-07`), which is the real database key and the login username. First name is only a display label. This avoids collisions between candidates sharing a first name.
3. **API keys are credentials.** Each candidate has an Anthropic API key pasted in by the admin. It must be: stored **encrypted at rest**, transmitted only over **HTTPS**, revealed **only to the authenticated candidate it belongs to**, and **never written to logs**.
4. **No secrets in the frontend, repo, or logs.** All secrets (DB credentials, encryption key, session secret) live in server-side environment variables / a secrets file excluded from version control.
5. **HTTPS only.** No plaintext HTTP except Caddy's automatic redirect to HTTPS. No self-signed certificates — use a real domain and Let's Encrypt.
6. **Audit logging.** Record, with timestamps, every: login, password set/reset, slot booking, slot reassignment, file download, API-key reveal, question submission, and answer. This is the fairness/defensibility record.
7. **Right to erasure.** A single admin action purges ALL candidate data (see Phase 5). A retention date is stored as configuration.

---

## 4. Data model (implement as specified — do not improvise the schema)

Use clear, explicit tables. Suggested shape:

- **admin** — single admin account. `id`, `username`, `password_hash`, `created_at`.
- **candidate** — `id` (PK), `candidate_id` (unique, e.g. `cand-07`), `first_name`, `password_hash` (nullable until set), `password_set_token` (nullable, one-time), `password_set_token_expires_at`, `status` (`invited` / `active` / `disabled`), `api_key_encrypted` (nullable), `created_at`.
- **slot** — `id` (PK), `starts_at` (timestamptz), `capacity` (int, default 1), `created_at`. A slot is "open" if its booked count < capacity.
- **booking** — `id` (PK), `candidate_id` (FK, unique — a candidate has at most one booking), `slot_id` (FK), `booked_at`. Enforce single-occupancy and no-double-booking with DB constraints + transactional locking (see Phase 2).
- **question** — `id` (PK), `candidate_id` (FK), `body`, `asked_at`, `answer` (nullable), `answered_at` (nullable). Private to the asking candidate.
- **download_event** — `id`, `candidate_id` (FK), `file_key`, `downloaded_at`.
- **audit_log** — `id`, `actor` (candidate_id or `admin`), `action`, `detail`, `created_at`.
- **config** — key/value for `prep_window_days` (default 8), `retention_date` (**PLACEHOLDER — admin sets this; leave clearly marked and unset by default**), and any other tunables.

Passwords hashed with a strong adaptive hash (bcrypt or argon2). API keys encrypted with a symmetric key held in server env (e.g. Fernet/AES-GCM).

---

## 5. Core logic — the prep-window / unlock rule (read carefully)

This is the most important piece of business logic. Get it exactly right.

- `prep_window_days` (N) is an admin config value, default **8**.
- For a candidate booked into a slot starting at `slot.starts_at`:
  - **unlock_at = max(now_at_booking_time_or_later, slot.starts_at − N days)**
  - In practice: compute `nominal_unlock = slot.starts_at − N days`. If `nominal_unlock` is already in the past at the moment of booking, content unlocks **immediately**. Otherwise content unlocks at `nominal_unlock`, and the candidate sees a **countdown timer** to that moment.
  - **Effective prep time = min(N days, time between booking and slot).** This means a candidate who books a slot fewer than N days away gets less than the full window — this is intended and must be shown honestly (next point).
- **At the booking screen, BEFORE the candidate confirms a slot**, display for the selected slot:
  - the assessment date/time,
  - the exact date their data will unlock,
  - the resulting number of prep days they will have.
  - e.g. *"If you choose this slot, your exercise data unlocks on **Mon 3 Nov**, giving you **8 days** to work on it before your assessment on **Tue 11 Nov**."*
- All currently-open slots are bookable (do NOT hide near slots) — the candidate chooses with full information about the trade-off.
- After booking: if unlocked, show the download area; if not yet unlocked, show a live countdown to `unlock_at` that automatically reveals the download area when it passes (no manual refresh required — poll or use the countdown to trigger a re-fetch).

---

## 6. Build phases

### Phase 1 — Foundations: stack, auth, accounts

- Scaffold the FastAPI backend, Vite/React frontend, Postgres, Docker Compose, and Caddy config (domain as a placeholder env var, e.g. `APP_DOMAIN`).
- Implement the data model from §4 with migrations.
- **Admin auth:** single admin, username + password, session-based login. Seed the admin account via an env-configured initial username + password (changeable later).
- **Candidate accounts (pre-created by admin):** admin creates a candidate with a first name; system assigns a `candidate_id`. On creation the candidate is `invited` with a one-time `password_set_token`. The admin is shown a **set-password link** (containing the token) to send manually — the app does not email it.
- **Candidate first login:** candidate opens the set-password link, chooses a password, account becomes `active`. Thereafter they log in with `candidate_id` + password. Single-factor is fine.
- Audit-log all auth events.

**Checkpoint:** admin can log in, create a candidate, retrieve a set-password link; candidate can set a password via that link and log in.

### Phase 2 — Slots & booking

- **Admin slot management:** create a slot (datetime + capacity, capacity defaults to 1); list all slots with booking status (open / booked / by which candidate); edit or delete an **unbooked** slot.
- **Protect booked slots:** a slot with a booking **cannot be deleted**. The admin must first reassign that candidate to another slot or release the booking. Reassignment recalculates the candidate's `unlock_at` based on the new slot. (No automatic candidate notification — the admin handles comms.)
- **Candidate booking:** candidate sees only currently-open slots. Selecting one shows the prep-window preview from §5 before confirmation.
- **Atomic reservation:** booking must be safe under concurrent attempts (correctness, even though simultaneous booking is unlikely since invites are spaced). Use a transaction with `SELECT … FOR UPDATE` on the slot row (or a unique constraint that prevents over-capacity) so two candidates cannot take the last seat. If a slot is taken while a candidate is on the confirmation screen, fail gracefully with a clear "that slot was just taken, please pick another" message and refresh availability.
- A candidate has **at most one booking** (DB-enforced). Slot changes are **admin-only** after booking.
- Audit-log bookings and reassignments.

**Checkpoint:** admin creates slots; candidate books one with an accurate prep-window preview; double-booking is impossible; booked slots are delete-protected.

### Phase 3 — Content delivery & API key reveal

- **Gated content:** the exercise brief, data files, and background reference are downloadable **only** when the candidate is `active`, has a booking, and `now >= unlock_at`. Before unlock, show the countdown (§5).
- **Files:** serve as proper streamed downloads (the wind-data file is large — ~150k rows of Excel — so stream it; do not load entire files into memory). Files are stored on the server filesystem (an admin-managed `content/` directory) — the admin can replace them without a redeploy if practical, otherwise document where they live.
- **File set** (admin places these; app just serves them):
  - the exercise brief,
  - the data files (turbine/component data, resources, weather limits, the 20-year hourly wind data),
  - background reference material (terminology, cranes, build process — deliberately more than needed; candidates judge relevance).
- **API key reveal:** once content is unlocked, the candidate's dashboard shows their Anthropic API key (decrypted server-side, sent over HTTPS, shown to that candidate only). Display a short note: *this key is for the LLM features your application uses at runtime; it has a fixed budget; track your own spend from the token usage returned in API responses.* The platform does NOT track or enforce spend — the $20 cap is enforced by Anthropic at the workspace level.
- **Admin pastes keys:** in the admin candidate view, the admin pastes a pre-created Anthropic workspace key into the candidate's record; it is encrypted on save. (Key creation and the $20 cap are done manually by the admin in the Anthropic Console — out of scope for this app.)
- Audit-log every download and every key reveal.

**Checkpoint:** locked candidate sees a countdown; unlocked candidate downloads files and sees their API key; downloads stream correctly; keys are encrypted at rest and never logged.

### Phase 4 — Q&A & admin area

- **Candidate Q&A:** an authenticated candidate can submit a question (free text) and see their own questions and any answers. Questions are **private to that candidate** — no candidate ever sees another's questions or answers. Display a clear expectation: *questions are answered by a person, typically within [admin-set SLA wording]; this is not a chatbot.*
- **Admin question queue:** the admin sees all questions across candidates (with which candidate asked), writes an answer, and the answer becomes visible to that candidate. Unanswered questions are clearly flagged.
- **Admin account management:** reset a candidate's password (regenerate a one-time set-password link), regenerate/re-issue the invite link, disable/re-enable an account.
- **Admin activity view:** a table showing, per candidate: status, booked slot, unlock time, whether they've logged in, whether/when they've downloaded each file, whether their key has been revealed, and question count. This is the at-a-glance fairness/monitoring view, drawn from the audit log and events.
- Audit-log questions and answers.

**Checkpoint:** candidate asks a question and sees the admin's answer privately; admin answers from the queue, manages accounts, and sees the activity overview.

### Phase 5 — Ops: HTTPS, backups, purge, CI

- **HTTPS:** Caddy configured for the real domain (`APP_DOMAIN` env var), automatic Let's Encrypt issuance and renewal, HTTP→HTTPS redirect. Document the one-line DNS step (point the domain's A record at the Hetzner box's IP) in the README.
- **Backups:** automated daily Postgres backup (e.g. `pg_dump` on a cron in a small sidecar or host cron), retained locally with a short rotation. Document restore steps. This protects booking and Q&A records mid-process.
- **Data purge (right to erasure):** a single, clearly-guarded admin action ("Purge all candidate data") that deletes all candidate, booking, question, download_event, and candidate-attributable audit records — a clean end-of-process wipe. Require an explicit typed confirmation. The `retention_date` config value is displayed as a reminder but the purge is manual (admin-triggered), not automatic.
- **Config admin:** admin UI to view/set `prep_window_days` and `retention_date` (the latter a **clearly-marked placeholder, unset by default**).
- **CI (GitHub Actions):** on push — run backend linting (ruff/flake8) and tests (pytest), frontend lint and build, and build the Docker images. Keep it simple; no deploy automation required unless trivial.
- **README:** setup, env vars (incl. `APP_DOMAIN`, DB creds, `ENCRYPTION_KEY`, `SESSION_SECRET`, initial admin creds), the manual steps the admin performs (create Anthropic workspaces + keys + $20 caps in the Console, paste keys, place content files, send invite/set-password links and the login URL by email manually), DNS step, backup/restore, and the purge action.

**Checkpoint:** app serves over HTTPS on the domain; backups run; purge works behind confirmation; CI is green.

---

## 7. Things to deliberately NOT do

- No self-service candidate registration — accounts are admin-created only.
- No email sending of any kind — all candidate comms are manual by the admin.
- No spend tracking or enforcement in the app — Anthropic's workspace cap handles it.
- No shared/public question board — Q&A is strictly private per candidate.
- No microservices, queues, Redis, or extra infrastructure.
- No storing of any personal data beyond first name + system candidate ID.
- No automatic notifications to candidates on admin actions (admin controls comms).

---

## 8. Open items to confirm with the human before/while building

- The exact **SLA wording** for the Q&A expectation ("answered within X hours").
- The **domain name** (fill `APP_DOMAIN` once registered).
- The **content files** are provided by the admin and not part of this build — confirm the expected filenames/directory so the download routes match.
- Visual design is unspecified — keep it clean, professional, and accessible; the candidate-facing side should feel like a considered recruitment experience, the admin side can be plain and functional. Match the organisation's brand colours if assets are provided.
