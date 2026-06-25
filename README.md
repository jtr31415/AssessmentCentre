# Assessment Platform

An internal recruitment-assessment web application for a single admin and approximately 15 candidates. The platform is data-protection-first: only a candidate's first name is stored; each candidate's Anthropic API key is Fernet-encrypted at rest and revealed only to the owning candidate; every admin and candidate action is written to an immutable audit log; and all traffic is served exclusively over HTTPS. Stack: FastAPI (Python 3.12) + React/Vite + PostgreSQL 16 + Caddy 2 + Docker Compose.

---

## Table of Contents

1. [Local Development](#local-development)
2. [Environment Variables](#environment-variables)
3. [Production Deploy (Hetzner VPS)](#production-deploy-hetzner-vps)
4. [Manual Admin Steps](#manual-admin-steps)
5. [Backups & Restore](#backups--restore)
6. [Right to Erasure / Purge](#right-to-erasure--purge)
7. [Security Notes](#security-notes)
8. [Project Layout](#project-layout)

---

## Local Development

### Prerequisites

- Docker (with the Compose plugin)
- Node.js 20+ (for the frontend dev server only)

### 1. Configure environment

```sh
cp .env.example .env
```

Generate a Fernet encryption key and a random session secret:

```sh
python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())"
```

Paste the output as `ENCRYPTION_KEY` in `.env`. Generate a separate random string (32+ characters) for `SESSION_SECRET`. **Never commit `.env`.**

### 2. Start the backend stack

```sh
docker compose -f compose.local.yaml up --build
```

This starts `db` (Postgres on port 5432) and `backend` (FastAPI on port 8000).

**Migrations run automatically on boot** — the backend entrypoint runs `alembic upgrade head` before starting uvicorn, so the schema is always up to date.

### 3. Start the frontend dev server

```sh
cd frontend
npm install
npm run dev
```

Vite proxies `/api/*` requests to `http://localhost:8000`, so the SPA and API work together without any extra config.

### Running tests

Tests require a running Postgres instance and the `TEST_DATABASE_URL` environment variable to be set.

The local compose stack exposes Postgres on port 5432, so from `backend/`:

```sh
TEST_DATABASE_URL=postgresql+psycopg://app:app@localhost:5432/app_test pytest
```

(`app_test` is created automatically by `scripts/init-test-db.sh` which is mounted into the local compose db service.)

---

## Environment Variables

Copy `.env.example` to `.env` and fill in all values. Secrets (`ENCRYPTION_KEY`, `SESSION_SECRET`, `INITIAL_ADMIN_PASSWORD`) are server-side only — never expose them to the frontend or commit them to source control.

| Variable | Purpose | Example / Default |
|---|---|---|
| `APP_DOMAIN` | Public domain name; used by Caddy for TLS and routing | `assessment.example.com` |
| `DATABASE_URL` | SQLAlchemy connection URL for the backend | `postgresql+psycopg://app:app@db:5432/app` |
| `POSTGRES_USER` | Postgres superuser name (used by the `db` service) | `app` |
| `POSTGRES_PASSWORD` | Postgres superuser password | `app` |
| `POSTGRES_DB` | Postgres database name | `app` |
| `ENCRYPTION_KEY` | Fernet key for encrypting API keys at rest — generate with the command above | *(generated)* |
| `SESSION_SECRET` | HMAC secret for signed session cookies | *(32+ random chars)* |
| `INITIAL_ADMIN_USERNAME` | Username created on first boot if no admin exists | `admin` |
| `INITIAL_ADMIN_PASSWORD` | Password for the initial admin account — change immediately after first login | `change-me` |
| `PREP_WINDOW_DAYS` | Number of days before assessment day that candidate prep materials become accessible | `8` |
| `DISPLAY_TIMEZONE` | Timezone used for displaying dates/times in the UI | `Europe/London` |

---

## Production Deploy (Hetzner VPS)

### 1. DNS

Point your domain's A record at the VPS IP address. For example, using your registrar's control panel:

```
assessment.example.com.  A  <VPS_IP>
```

Allow a few minutes for propagation before starting Caddy.

### 2. Build the frontend

Caddy serves the pre-built SPA from `frontend/dist`. Build it once before starting the stack (and after any frontend changes):

```sh
cd frontend
npm install
npm run build
```

### 3. Configure and start

Set all variables in `.env`, including `APP_DOMAIN` (your real domain) and strong random values for `ENCRYPTION_KEY`, `SESSION_SECRET`, and `INITIAL_ADMIN_PASSWORD`.

```sh
docker compose up -d --build
```

This starts four services:

| Service | Role |
|---|---|
| `db` | PostgreSQL 16 (internal only, no port exposed) |
| `backend` | FastAPI on internal port 8000 (runs migrations on boot) |
| `caddy` | Reverse proxy on ports 80 + 443; auto-issues Let's Encrypt TLS for `APP_DOMAIN`; proxies `/api/*` to `backend:8000`; serves `frontend/dist` for all other paths |
| `backup` | Postgres dump sidecar (runs daily; see [Backups](#backups--restore)) |

Caddy automatically issues and renews a Let's Encrypt certificate for `APP_DOMAIN` and redirects all HTTP traffic to HTTPS.

---

## Manual Admin Steps

**The platform sends no email.** The following steps must be performed by the admin manually.

### Anthropic Console setup (per candidate)

1. In the [Anthropic Console](https://console.anthropic.com/), create a new workspace for each candidate.
2. Generate an API key in that workspace.
3. Set a usage cap of approximately **$20** on the workspace to limit spend.

### Adding candidates in the admin UI

1. Log in to the admin UI with the `INITIAL_ADMIN_USERNAME` credentials.
2. Navigate to **Candidates → Add candidate** and create a record (first name only is stored).
3. Paste the candidate's Anthropic API key into the key field (write-only; the key is encrypted immediately and never displayed again).
4. After saving, the UI shows a **one-time set-password link** for that candidate. Copy it.
5. **Email the candidate manually** with:
   - Their one-time set-password link (single use; expires after first visit)
   - The login URL (`https://<APP_DOMAIN>`)

### Content files

The platform serves assessment files from `backend/content/`. You must place the real files there with **exactly** these filenames (from `backend/app/content_manifest.py`):

```
backend/content/
├── exercise_brief.pdf
├── turbine_data.csv
├── weather_limits.csv
├── wind_data_20yr.xlsx
├── terminology.pdf
└── build_process.pdf
```

Only filenames listed in the manifest can ever be served. Any file with a different name will not be accessible.

---

## Backups & Restore

The `backup` sidecar service runs `scripts/backup.sh` once every 24 hours. Dumps are written to the `backups` Docker named volume as gzip-compressed plain-SQL files:

```
/backups/assessment-YYYYMMDD-HHMMSS.sql.gz
```

Dumps older than 7 days are deleted automatically.

### On-demand backup

```sh
docker compose run --rm backup sh /backup.sh
```

### Restore

See [`scripts/restore.md`](scripts/restore.md) for full step-by-step instructions, including how to stop the app, list available dumps, and restore via a one-off container or a local `psql` client.

> **Security:** Dumps contain sensitive data (encrypted keys, password hashes, all user data). Store and transfer them over secure channels only.

---

## Right to Erasure / Purge

Admin → **Settings & data** → **Danger zone**

To permanently delete all candidate data, type the exact confirmation phrase:

```
PURGE ALL CANDIDATE DATA
```

This deletes: all candidate records, bookings, questions, downloads, and candidate-attributed audit rows.

This **keeps**: admin accounts, platform configuration, time slots, and admin-attributed audit rows.

**`retention_date`** (set in Settings & data → Config) is a manual reminder field only. It is displayed to the admin as a prompt to consider erasure — it never triggers automatic deletion.

---

## Security Notes

- **Minimal personal data:** only a candidate's first name is stored. `candidate_id` is an internal system identifier, not a personal identifier.
- **Encrypted API keys:** Anthropic API keys are Fernet-encrypted at rest. They are revealed only to the owning candidate at the moment they unlock their key, and are never exposed to the admin after initial entry.
- **Audit log:** all significant admin and candidate actions are recorded with a timestamp and actor. The log is append-only.
- **HTTPS-only:** Caddy issues TLS automatically via Let's Encrypt and redirects all HTTP traffic to HTTPS. The backend is not exposed directly.
- **Disabled candidates:** disabling a candidate account takes effect immediately; they cannot log in or access any resource.

---

## Project Layout

```
Assessment/
├── backend/               # FastAPI application (Python 3.12)
│   ├── app/               # Application code
│   ├── alembic/           # Database migrations
│   ├── content/           # Assessment files (not committed; see manifest)
│   ├── tests/             # Pytest test suite
│   ├── Dockerfile
│   ├── docker-entrypoint.sh
│   └── pyproject.toml
├── frontend/              # React + Vite SPA
│   └── dist/              # Built output served by Caddy (generated; not committed)
├── caddy/
│   └── Caddyfile          # Reverse proxy + TLS config
├── scripts/
│   ├── backup.sh          # pg_dump script (run by backup sidecar)
│   ├── restore.md         # Restore procedure
│   └── init-test-db.sh    # Creates app_test DB for local testing
├── compose.yaml           # Production compose (db, backend, caddy, backup)
├── compose.local.yaml     # Local dev compose (db, backend only)
└── .env.example           # Environment variable template
```
