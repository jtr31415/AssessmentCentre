# Design — Candidate Assessment Platform

**Date:** 2026-06-24
**Source spec:** `platform_build_spec.md`
**Status:** Approved for implementation

This design document records the decisions made on top of the build spec. The
build spec is authoritative for *what* to build; this document records *how* and
the open-item resolutions agreed with the human. Where this document and the
spec agree, the spec wins; where this document resolves an ambiguity, this
document wins.

---

## 1. Scope & intent

A small internal recruitment-assessment web app for **one admin** and **~15
candidates**. The admin pre-creates candidate accounts, candidates book one
assessment slot, and a fixed number of days before the slot they unlock
downloadable exercise files plus their own Anthropic API key. Private,
human-answered Q&A runs alongside. Boring monolith: FastAPI + React + Postgres +
Caddy on a single Hetzner VPS via Docker Compose.

Correctness, clarity, and data protection are the priorities. Load is trivial.

## 2. Resolved open items

These extend / pin down the build spec:

| Item | Decision |
|------|----------|
| Deploy infrastructure | **None provisioned yet.** Build + fully test locally; author all deploy config (Caddy, Compose, README, CI). Real deploy deferred until VPS + domain exist. |
| Content files | **Placeholders.** Download system is config-driven via a file manifest; admin drops real files into `content/` later. Nothing blocks on real files. |
| Purge vs audit (§3.6 / §5 tension) | **Delete (per spec §5).** Purge fully deletes candidate-attributable audit rows — a clean wipe, strongest erasure guarantee. |
| API key encryption | **Fernet** (`cryptography` library): authenticated, simple key handling. |
| Countdown to unlock | **Client-side poll** of `unlock_at`; re-fetch when the timer reaches zero. No websockets. |
| Q&A SLA wording | **Admin-editable `config` value** (`qa_sla_text`), with a placeholder default. Not hardcoded. |
| Cookie consent banner | **Not required and not added.** The only cookie is a strictly-necessary session/auth cookie (exempt under UK PECR / EU ePrivacy). Instead we ship a static **privacy notice** page (`/privacy`) for GDPR transparency. |
| Display timezone | `config` value `display_timezone`, default `Europe/London`. All timestamps stored UTC. |

## 3. Repository layout

```
assessment/
├── backend/                    # FastAPI app
│   ├── app/
│   │   ├── main.py             # app factory, middleware, router mount
│   │   ├── config.py           # env settings (pydantic-settings)
│   │   ├── db.py               # SQLAlchemy engine/session
│   │   ├── models.py           # the §4 tables
│   │   ├── security.py         # bcrypt hashing, Fernet encrypt/decrypt, sessions
│   │   ├── audit.py            # single choke-point for audit_log writes
│   │   ├── deps.py             # auth deps (current_admin / current_candidate)
│   │   ├── routers/            # auth.py, admin.py, candidate.py, content.py, qa.py, public.py
│   │   └── content_manifest.py # config-driven file list (placeholders)
│   ├── alembic/                # migrations
│   ├── content/                # admin-managed files (gitignored, placeholder files)
│   ├── tests/                  # pytest
│   └── pyproject.toml          # ruff + pytest config
├── frontend/                   # Vite + React (TypeScript)
│   └── src/
│       ├── api/                # typed fetch client
│       ├── pages/              # candidate + admin pages, /privacy
│       └── components/         # countdown, slot picker, etc.
├── caddy/Caddyfile             # prod TLS config (APP_DOMAIN)
├── compose.yaml                # prod-ish: backend, frontend(static via Caddy), postgres, caddy
├── compose.local.yaml          # local override: no Let's Encrypt, http/localhost
├── .github/workflows/ci.yml
├── .env.example
└── README.md
```

**Local testing reality:** Let's Encrypt cannot issue certs for `localhost`, so
`compose.local.yaml` runs Caddy with its internal/local CA (or plain HTTP on a
localhost port). The full stack runs and is testable end-to-end locally; the
real-domain TLS path is exercised only on deploy. Same images, different
Caddyfile/override.

## 4. Data model

Tables exactly per build-spec §4 (`admin`, `candidate`, `slot`, `booking`,
`question`, `download_event`, `audit_log`, `config`). Implementation notes:

- **Booking atomicity:** `booking.candidate_id` UNIQUE (one booking per
  candidate) + transactional `SELECT … FOR UPDATE` on the slot row, re-checking
  `booked_count < capacity` inside the lock. Loser receives a clean HTTP 409 →
  "that slot was just taken, please pick another."
- **`unlock_at` stored on the booking row** at booking time
  (`max(booked_at, slot.starts_at − N days)`), so the value is stable and
  auditable even if `prep_window_days` later changes. Reassignment recomputes it.
- **Timestamps** all `timestamptz`, stored UTC; frontend formats to
  `display_timezone`.
- **Audit writes go through one `audit.py` helper** so nothing is missed and the
  API key is structurally impossible to log (the helper never accepts the key).
- **`config` seeds:** `prep_window_days=8`, `retention_date=null`
  (clearly-marked placeholder), `qa_sla_text=<placeholder>`,
  `display_timezone=Europe/London`, plus privacy-notice text.

## 5. Prep-window / unlock rule (build-spec §5)

The core business logic. `unlock_at = max(now_at_booking, slot.starts_at − N days)`.

- If `nominal_unlock = slot.starts_at − N days` is already past at booking,
  content unlocks immediately; otherwise unlocks at `nominal_unlock` with a
  live countdown.
- Effective prep time = `min(N days, time between booking and slot)`. A late
  booker gets less than the full window — shown honestly.
- **Booking preview (before confirm)** shows: assessment date/time, exact unlock
  date, and resulting prep days. All open slots remain bookable.
- After booking: unlocked → download area; locked → countdown that
  self-reveals the download area on expiry (poll-on-expiry, no manual refresh).

## 6. Auth & sessions

- **Sessions:** signed HTTP-only, Secure cookies (server-side `SESSION_SECRET`).
  One mechanism for admin and candidate, distinguished by role on the session.
  No JWT.
- **Admin** seeded from env on first boot (`INITIAL_ADMIN_USERNAME` /
  `INITIAL_ADMIN_PASSWORD`), changeable later.
- **Candidate set-password token:** one-time, expiring, single-use; consumed on
  password set, account → `active`. Admin UI displays the link; the app never
  emails it.
- **Passwords:** bcrypt. **API keys:** Fernet with `ENCRYPTION_KEY` from env.

## 7. Privacy notice (`/privacy`)

Static page linked from the footer of both candidate and admin areas. Text
driven by the `config` table so the admin can adjust wording. Content covers:

- **Data held:** first name, system ID (`cand-07`), booking, downloads,
  questions, and an encrypted API key.
- **Not held:** no email, surname, phone, IP/analytics tracking, or marketing.
- **Cookie:** one essential session cookie, removed on logout/expiry.
- **Retention & erasure:** held until the assessment process ends, then purged;
  right to erasure honoured via the §5 admin purge action.

No cookie consent banner — see §2 rationale.

## 8. Build & test rhythm

Execute the build-spec's five phases in order. At each phase **checkpoint**,
stop and demonstrate it working locally (UI / curl walkthrough + relevant green
pytest) before proceeding — that is the review gate.

- **Phase 1** — Foundations: stack scaffold, data model + migrations, admin
  auth, candidate accounts + set-password flow, `/privacy` page, audit logging.
- **Phase 2** — Slots & booking (atomic reservation, delete-protection,
  prep-window preview).
- **Phase 3** — Content delivery (gated, streamed downloads) & API key reveal.
- **Phase 4** — Q&A (private per candidate) & admin area (question queue,
  account management, activity view).
- **Phase 5** — Ops: HTTPS/Caddy, backups, purge, config admin, CI, README.

Tests written alongside each phase, TDD where it matters most: prep-window math,
booking concurrency, auth/token flows, encryption round-trip, content-gating
rules. CI: ruff + pytest + frontend lint/build + Docker image build.

## 9. Explicit non-goals (build-spec §7)

No self-service registration, no email sending, no spend tracking, no shared
question board, no microservices/queues/Redis, no personal data beyond first
name + candidate ID, no automatic candidate notifications.
