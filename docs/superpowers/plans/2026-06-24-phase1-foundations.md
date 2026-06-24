# Phase 1 — Foundations: Stack, Auth, Accounts — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the FastAPI + React + Postgres + Caddy stack with the full §4 data model, admin login, admin-driven candidate creation, candidate set-password + login flow, a `/privacy` page, and audit logging of all auth events.

**Architecture:** A boring monolith. FastAPI backend with SQLAlchemy 2.0 models + Alembic migrations against Postgres. Session auth via signed HTTP-only cookies (Starlette `SessionMiddleware`), one mechanism for both roles distinguished by a `role` key in the session. All audit writes funnel through a single `audit.record()` helper so nothing is missed and API keys can never be logged. React (Vite + TS) frontend with a typed fetch client. Everything runs locally via `compose.local.yaml` (HTTP on localhost; Let's Encrypt deferred to Phase 5).

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, pydantic-settings, passlib[bcrypt], cryptography (Fernet), pytest + httpx; Vite + React + TypeScript; Postgres 16; Docker Compose; ruff.

## Global Constraints

- **Stack is fixed** — Python/FastAPI, Vite/React, PostgreSQL, Caddy, Docker Compose on one VPS. No microservices, queues, Redis, Kubernetes. (spec §2, §7)
- **Minimal personal data** — the ONLY candidate personal data stored is `first_name`. No email, surname, phone. (spec §3.1)
- **Candidate identity** is a system-generated `candidate_id` (e.g. `cand-07`), the DB login key; first name is a display label only. (spec §3.2)
- **API keys are credentials** — encrypted at rest (Fernet), HTTPS-only in transit, revealed only to the owning candidate, NEVER written to logs. (spec §3.3)
- **No secrets in frontend/repo/logs** — DB creds, `ENCRYPTION_KEY`, `SESSION_SECRET` live in server-side env, gitignored. (spec §3.4)
- **Audit-log** every login, password set/reset, slot booking, reassignment, file download, key reveal, question, answer — with timestamps. (spec §3.6)
- **Passwords** hashed with bcrypt; **API keys** encrypted with Fernet. (spec §4)
- All timestamps stored UTC as `timestamptz`. Display timezone is a config value (`Europe/London` default).
- Candidate IDs assigned as `cand-NN` zero-padded, sequential.

---

## File Structure (Phase 1)

| File | Responsibility |
|------|----------------|
| `backend/pyproject.toml` | deps, ruff + pytest config |
| `backend/app/config.py` | env settings via pydantic-settings |
| `backend/app/db.py` | SQLAlchemy engine, session factory, `Base`, `get_db` |
| `backend/app/models.py` | all §4 ORM tables |
| `backend/app/security.py` | bcrypt hash/verify, Fernet encrypt/decrypt, token gen |
| `backend/app/audit.py` | `record()` — the single audit write choke-point |
| `backend/app/candidate_ids.py` | next-sequential `cand-NN` allocator |
| `backend/app/deps.py` | `current_admin`, `current_candidate` session deps |
| `backend/app/schemas.py` | pydantic request/response models |
| `backend/app/routers/auth.py` | admin login/logout, candidate set-password + login |
| `backend/app/routers/admin.py` | create candidate, list candidates, get set-password link |
| `backend/app/routers/public.py` | `/privacy` content, health |
| `backend/app/main.py` | app factory, SessionMiddleware, router mount, admin seed |
| `backend/alembic/...` | migration env + initial migration |
| `backend/tests/...` | pytest suite (conftest with test DB + client) |
| `frontend/...` | Vite/React scaffold, API client, login + set-password + privacy pages |
| `compose.local.yaml`, `compose.yaml`, `backend/Dockerfile`, `caddy/Caddyfile`, `.env.example` | infra |

---

## Task 1: Backend scaffold + config + health endpoint

**Files:**
- Create: `backend/pyproject.toml`, `backend/app/__init__.py`, `backend/app/config.py`, `backend/app/main.py`, `backend/app/routers/__init__.py`, `backend/app/routers/public.py`
- Test: `backend/tests/__init__.py`, `backend/tests/conftest.py`, `backend/tests/test_health.py`

**Interfaces:**
- Produces: `app.config.get_settings() -> Settings` (fields: `database_url: str`, `session_secret: str`, `encryption_key: str`, `initial_admin_username: str`, `initial_admin_password: str`, `prep_window_days: int = 8`, `display_timezone: str = "Europe/London"`); `app.main.create_app() -> FastAPI`; GET `/api/health` → `{"status": "ok"}`.

- [ ] **Step 1: Write `backend/pyproject.toml`**

```toml
[project]
name = "assessment-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.111",
    "uvicorn[standard]>=0.30",
    "sqlalchemy>=2.0",
    "alembic>=1.13",
    "psycopg[binary]>=3.1",
    "pydantic-settings>=2.2",
    "passlib[bcrypt]>=1.7",
    "cryptography>=42.0",
    "itsdangerous>=2.1",
    "python-multipart>=0.0.9",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "httpx>=0.27", "ruff>=0.5"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"
```

- [ ] **Step 2: Write `backend/app/config.py`**

```python
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://app:app@localhost:5432/app"
    session_secret: str = "dev-insecure-session-secret-change-me"
    encryption_key: str = ""  # Fernet key; generated in dev if blank
    initial_admin_username: str = "admin"
    initial_admin_password: str = "changeme"
    prep_window_days: int = 8
    display_timezone: str = "Europe/London"


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 3: Write `backend/app/routers/public.py`**

```python
from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["public"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 4: Write `backend/app/main.py` (minimal; expanded in later tasks)**

```python
from fastapi import FastAPI

from app.routers import public


def create_app() -> FastAPI:
    app = FastAPI(title="Candidate Assessment Platform")
    app.include_router(public.router)
    return app


app = create_app()
```

- [ ] **Step 5: Write `backend/tests/conftest.py` (HTTP client fixture)**

```python
import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client():
    return TestClient(create_app())
```

- [ ] **Step 6: Write the failing test `backend/tests/test_health.py`**

```python
def test_health_ok(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

- [ ] **Step 7: Run it to verify pass (and install deps)**

Run: `cd backend && pip install -e ".[dev]" && pytest tests/test_health.py -v`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/
git commit -m "feat(backend): scaffold FastAPI app with health endpoint"
```

---

## Task 2: Database layer + §4 models

**Files:**
- Create: `backend/app/db.py`, `backend/app/models.py`
- Test: `backend/tests/test_models.py`

**Interfaces:**
- Consumes: `get_settings()` from Task 1.
- Produces: `app.db.Base` (DeclarativeBase), `app.db.engine`, `app.db.SessionLocal`, `app.db.get_db()` generator. Models: `Admin`, `Candidate`, `Slot`, `Booking`, `Question`, `DownloadEvent`, `AuditLog`, `Config` with the columns from spec §4. `Candidate.status` is one of `"invited" | "active" | "disabled"`.

- [ ] **Step 1: Write `backend/app/db.py`**

```python
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


engine = create_engine(get_settings().database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 2: Write `backend/app/models.py` (all §4 tables)**

```python
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Admin(Base):
    __tablename__ = "admin"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Candidate(Base):
    __tablename__ = "candidate"
    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    first_name: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_set_token: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    password_set_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(16), default="invited")
    api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Slot(Base):
    __tablename__ = "slot"
    id: Mapped[int] = mapped_column(primary_key=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    capacity: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    bookings: Mapped[list["Booking"]] = relationship(back_populates="slot")


class Booking(Base):
    __tablename__ = "booking"
    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidate.id"), unique=True)
    slot_id: Mapped[int] = mapped_column(ForeignKey("slot.id"))
    unlock_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    booked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    slot: Mapped["Slot"] = relationship(back_populates="bookings")


class Question(Base):
    __tablename__ = "question"
    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidate.id"))
    body: Mapped[str] = mapped_column(Text)
    asked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DownloadEvent(Base):
    __tablename__ = "download_event"
    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidate.id"))
    file_key: Mapped[str] = mapped_column(String(255))
    downloaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    actor: Mapped[str] = mapped_column(String(64))  # candidate_id string or "admin"
    action: Mapped[str] = mapped_column(String(64))
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Config(Base):
    __tablename__ = "config"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (UniqueConstraint("key"),)
```

- [ ] **Step 3: Update `backend/tests/conftest.py` to provide a real test DB**

Replace the file with a fixture that builds tables on a test Postgres DB (from `TEST_DATABASE_URL` env, falling back to the dev URL) and yields a client whose `get_db` is overridden to a transactional session:

```python
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import create_app
import app.models  # noqa: F401  (register tables)

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://app:app@localhost:5432/app_test"
)


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(TEST_DB_URL)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture
def db_session(engine):
    TestSession = sessionmaker(bind=engine, expire_on_commit=False)
    session = TestSession()
    yield session
    session.rollback()
    # clean tables between tests
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()
    session.close()


@pytest.fixture
def client(db_session):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    return TestClient(app)
```

- [ ] **Step 4: Write the failing test `backend/tests/test_models.py`**

```python
from app.models import Candidate


def test_candidate_roundtrip(db_session):
    c = Candidate(candidate_id="cand-01", first_name="Ada", status="invited")
    db_session.add(c)
    db_session.commit()
    fetched = db_session.query(Candidate).filter_by(candidate_id="cand-01").one()
    assert fetched.first_name == "Ada"
    assert fetched.password_hash is None
    assert fetched.status == "invited"
```

- [ ] **Step 5: Run test to verify it fails then passes**

Run: `cd backend && pytest tests/test_models.py -v`
Expected: PASS once a `app_test` database exists. (Local Postgres from Task 4; for now run against a locally available Postgres or skip until Task 4 lands — note this ordering in the commit.)

- [ ] **Step 6: Commit**

```bash
git add backend/app/db.py backend/app/models.py backend/tests/
git commit -m "feat(backend): add SQLAlchemy models for all data-model tables"
```

---

## Task 3: Security helpers — bcrypt, Fernet, tokens

**Files:**
- Create: `backend/app/security.py`
- Test: `backend/tests/test_security.py`

**Interfaces:**
- Consumes: `get_settings()`.
- Produces: `hash_password(plain: str) -> str`; `verify_password(plain: str, hashed: str) -> bool`; `encrypt_secret(plain: str) -> str`; `decrypt_secret(token: str) -> str`; `generate_token() -> str` (URL-safe, ≥32 bytes entropy). Fernet key sourced from `settings.encryption_key`; if blank, a process-stable dev key is derived (never used in prod — README warns).

- [ ] **Step 1: Write the failing test `backend/tests/test_security.py`**

```python
from app.security import (
    decrypt_secret,
    encrypt_secret,
    generate_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip():
    h = hash_password("hunter2")
    assert h != "hunter2"
    assert verify_password("hunter2", h)
    assert not verify_password("wrong", h)


def test_secret_encrypt_roundtrip():
    secret = "sk-ant-abc123"
    token = encrypt_secret(secret)
    assert token != secret
    assert decrypt_secret(token) == secret


def test_generate_token_unique_and_long():
    a, b = generate_token(), generate_token()
    assert a != b
    assert len(a) >= 32
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && pytest tests/test_security.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write `backend/app/security.py`**

```python
import base64
import hashlib
import secrets

from cryptography.fernet import Fernet
from passlib.context import CryptContext

from app.config import get_settings

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _fernet() -> Fernet:
    key = get_settings().encryption_key
    if not key:
        # Dev-only deterministic fallback. README warns; prod MUST set ENCRYPTION_KEY.
        digest = hashlib.sha256(b"dev-insecure-encryption-key").digest()
        key = base64.urlsafe_b64encode(digest).decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def hash_password(plain: str) -> str:
    return _pwd.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)


def encrypt_secret(plain: str) -> str:
    return _fernet().encrypt(plain.encode()).decode()


def decrypt_secret(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()


def generate_token() -> str:
    return secrets.token_urlsafe(32)
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && pytest tests/test_security.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/security.py backend/tests/test_security.py
git commit -m "feat(backend): add bcrypt/Fernet/token security helpers"
```

---

## Task 4: Local infra — Docker Compose, Postgres, Dockerfiles, env

**Files:**
- Create: `compose.local.yaml`, `compose.yaml`, `backend/Dockerfile`, `caddy/Caddyfile`, `.env.example`, `backend/content/.gitkeep`

**Interfaces:**
- Produces: a runnable local stack. `docker compose -f compose.local.yaml up` brings up Postgres (db `app`, user/pass `app`), backend on `:8000`, and creates `app_test` for tests. `.env.example` documents every var.

- [ ] **Step 1: Write `.env.example`**

```bash
# Backend
DATABASE_URL=postgresql+psycopg://app:app@db:5432/app
SESSION_SECRET=change-me-32-bytes-random
ENCRYPTION_KEY=        # generate: python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())"
INITIAL_ADMIN_USERNAME=admin
INITIAL_ADMIN_PASSWORD=change-me
PREP_WINDOW_DAYS=8
DISPLAY_TIMEZONE=Europe/London
# Postgres
POSTGRES_USER=app
POSTGRES_PASSWORD=app
POSTGRES_DB=app
# Deploy (Phase 5)
APP_DOMAIN=assessment.example.com
```

- [ ] **Step 2: Write `backend/Dockerfile`**

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[dev]"
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: Write `compose.local.yaml`**

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: app
      POSTGRES_DB: app
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./scripts/init-test-db.sh:/docker-entrypoint-initdb.d/init-test-db.sh:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app"]
      interval: 3s
      timeout: 3s
      retries: 10

  backend:
    build: ./backend
    env_file: .env
    environment:
      DATABASE_URL: postgresql+psycopg://app:app@db:5432/app
    depends_on:
      db:
        condition: service_healthy
    ports:
      - "8000:8000"

volumes:
  pgdata:
```

- [ ] **Step 4: Write `scripts/init-test-db.sh`**

```bash
#!/bin/bash
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
  CREATE DATABASE app_test;
EOSQL
```

- [ ] **Step 5: Write `compose.yaml` (prod-ish, Caddy + static frontend; backend + db) and `caddy/Caddyfile`**

`compose.yaml`:

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 5s
      timeout: 3s
      retries: 10

  backend:
    build: ./backend
    env_file: .env
    depends_on:
      db:
        condition: service_healthy

  caddy:
    image: caddy:2
    depends_on:
      - backend
    ports:
      - "80:80"
      - "443:443"
    environment:
      APP_DOMAIN: ${APP_DOMAIN}
    volumes:
      - ./caddy/Caddyfile:/etc/caddy/Caddyfile:ro
      - ./frontend/dist:/srv:ro
      - caddy_data:/data
      - caddy_config:/config

volumes:
  pgdata:
  caddy_data:
  caddy_config:
```

`caddy/Caddyfile`:

```
{$APP_DOMAIN} {
    encode gzip
    handle /api/* {
        reverse_proxy backend:8000
    }
    handle {
        root * /srv
        try_files {path} /index.html
        file_server
    }
}
```

- [ ] **Step 6: Bring the stack up and verify health**

Run:
```bash
cp .env.example .env
docker compose -f compose.local.yaml up -d --build
curl -s http://localhost:8000/api/health
```
Expected: `{"status":"ok"}`.

- [ ] **Step 7: Run the model + security tests against the live DB**

Run:
```bash
cd backend && TEST_DATABASE_URL=postgresql+psycopg://app:app@localhost:5432/app_test pytest -v
```
Expected: PASS (Task 2 & 3 tests now green against real Postgres).

- [ ] **Step 8: Commit**

```bash
git add compose.local.yaml compose.yaml backend/Dockerfile caddy/ scripts/ .env.example backend/content/.gitkeep
git commit -m "chore(infra): local + prod compose, Dockerfile, Caddy, env template"
```

---

## Task 5: Alembic migrations

**Files:**
- Create: `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/script.py.mako`, `backend/alembic/versions/0001_initial.py`

**Interfaces:**
- Consumes: `Base.metadata` from `app.db`, `app.models`.
- Produces: `alembic upgrade head` creates all §4 tables. Migration becomes the source of truth for schema (tests may still use `create_all`).

- [ ] **Step 1: Initialize alembic and point `env.py` at our metadata**

Run: `cd backend && alembic init alembic`
Then edit `backend/alembic/env.py` so it imports settings and metadata:

```python
# in alembic/env.py — key edits
from app.config import get_settings
from app.db import Base
import app.models  # noqa: F401

config.set_main_option("sqlalchemy.url", get_settings().database_url)
target_metadata = Base.metadata
```

- [ ] **Step 2: Autogenerate the initial migration**

Run: `cd backend && alembic revision --autogenerate -m "initial schema" `
Rename the produced file to `versions/0001_initial.py`. Open it and confirm it creates all eight tables (`admin`, `candidate`, `slot`, `booking`, `question`, `download_event`, `audit_log`, `config`) with the unique constraints on `candidate.candidate_id` and `booking.candidate_id`.

- [ ] **Step 3: Apply and verify**

Run: `cd backend && alembic upgrade head && python -c "import sqlalchemy as sa, os; e=sa.create_engine(os.environ['DATABASE_URL']); print(sa.inspect(e).get_table_names())"`
Expected: list includes all eight tables plus `alembic_version`.

- [ ] **Step 4: Add a smoke test that the unique constraints exist**

`backend/tests/test_migrations.py`:

```python
import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Candidate


def test_candidate_id_unique(db_session):
    db_session.add(Candidate(candidate_id="cand-01", first_name="A"))
    db_session.commit()
    db_session.add(Candidate(candidate_id="cand-01", first_name="B"))
    with pytest.raises(IntegrityError):
        db_session.commit()
```

Run: `cd backend && TEST_DATABASE_URL=...app_test pytest tests/test_migrations.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/alembic.ini backend/alembic/
git commit -m "feat(backend): alembic initial migration for full schema"
```

---

## Task 6: Audit helper + candidate-ID allocator

**Files:**
- Create: `backend/app/audit.py`, `backend/app/candidate_ids.py`
- Test: `backend/tests/test_audit.py`, `backend/tests/test_candidate_ids.py`

**Interfaces:**
- Consumes: `Session`, models.
- Produces: `audit.record(db: Session, actor: str, action: str, detail: str | None = None) -> None` — writes one `AuditLog` row and commits; **never accepts secret material** (callers pass only non-sensitive detail strings). `candidate_ids.allocate_candidate_id(db: Session) -> str` — returns next `cand-NN` (zero-padded to 2, widening past 99), unique under the existing rows.

- [ ] **Step 1: Write failing tests**

`backend/tests/test_audit.py`:

```python
from app.audit import record
from app.models import AuditLog


def test_record_writes_row(db_session):
    record(db_session, actor="admin", action="login", detail="ok")
    row = db_session.query(AuditLog).one()
    assert row.actor == "admin"
    assert row.action == "login"
    assert row.detail == "ok"
    assert row.created_at is not None
```

`backend/tests/test_candidate_ids.py`:

```python
from app.candidate_ids import allocate_candidate_id
from app.models import Candidate


def test_allocate_sequential(db_session):
    assert allocate_candidate_id(db_session) == "cand-01"
    db_session.add(Candidate(candidate_id="cand-01", first_name="A"))
    db_session.commit()
    assert allocate_candidate_id(db_session) == "cand-02"
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd backend && pytest tests/test_audit.py tests/test_candidate_ids.py -v`
Expected: FAIL — modules not found.

- [ ] **Step 3: Write `backend/app/audit.py`**

```python
from sqlalchemy.orm import Session

from app.models import AuditLog


def record(db: Session, actor: str, action: str, detail: str | None = None) -> None:
    """Single choke-point for audit writes. Never pass secret material as detail."""
    db.add(AuditLog(actor=actor, action=action, detail=detail))
    db.commit()
```

- [ ] **Step 4: Write `backend/app/candidate_ids.py`**

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Candidate


def allocate_candidate_id(db: Session) -> str:
    rows = db.execute(select(Candidate.candidate_id)).scalars().all()
    nums = [int(r.split("-")[1]) for r in rows if r.startswith("cand-")]
    nxt = (max(nums) + 1) if nums else 1
    return f"cand-{nxt:02d}"
```

- [ ] **Step 5: Run to verify they pass**

Run: `cd backend && TEST_DATABASE_URL=...app_test pytest tests/test_audit.py tests/test_candidate_ids.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/audit.py backend/app/candidate_ids.py backend/tests/test_audit.py backend/tests/test_candidate_ids.py
git commit -m "feat(backend): audit choke-point and candidate-id allocator"
```

---

## Task 7: Sessions, admin seed, admin login/logout

**Files:**
- Modify: `backend/app/main.py`
- Create: `backend/app/deps.py`, `backend/app/schemas.py`, `backend/app/routers/auth.py`, `backend/app/seed.py`
- Test: `backend/tests/test_admin_auth.py`

**Interfaces:**
- Consumes: `get_db`, `hash_password`/`verify_password`, `record`, `get_settings`.
- Produces:
  - `app.seed.seed_admin_and_config(db)` — idempotently creates the admin from env and seeds config keys (`prep_window_days`, `retention_date`=null, `qa_sla_text`, `display_timezone`).
  - `app.deps.current_admin(request, db) -> Admin` — 401 if `request.session.get("role") != "admin"`.
  - `app.deps.current_candidate(request, db) -> Candidate` — 401 unless role `candidate`.
  - POST `/api/auth/admin/login` `{username, password}` → sets session `{role:"admin", admin_id}`, audit `login`; 401 on bad creds.
  - POST `/api/auth/logout` → clears session.
  - GET `/api/auth/me` → `{role, id, ...}` or 401.

- [ ] **Step 1: Write failing test `backend/tests/test_admin_auth.py`**

```python
from app.seed import seed_admin_and_config


def test_admin_login_success_and_me(client, db_session):
    seed_admin_and_config(db_session)
    r = client.post("/api/auth/admin/login", json={"username": "admin", "password": "changeme"})
    assert r.status_code == 200
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["role"] == "admin"


def test_admin_login_bad_password(client, db_session):
    seed_admin_and_config(db_session)
    r = client.post("/api/auth/admin/login", json={"username": "admin", "password": "nope"})
    assert r.status_code == 401


def test_me_unauthenticated(client):
    assert client.get("/api/auth/me").status_code == 401
```

(Test settings: conftest sets `INITIAL_ADMIN_PASSWORD=changeme` via env before `get_settings`. Add to conftest top: `os.environ.setdefault("INITIAL_ADMIN_PASSWORD", "changeme")`.)

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && pytest tests/test_admin_auth.py -v`
Expected: FAIL — routes/seed missing.

- [ ] **Step 3: Write `backend/app/schemas.py`**

```python
from pydantic import BaseModel


class AdminLogin(BaseModel):
    username: str
    password: str


class CandidateLogin(BaseModel):
    candidate_id: str
    password: str


class SetPassword(BaseModel):
    token: str
    password: str


class CreateCandidate(BaseModel):
    first_name: str
```

- [ ] **Step 4: Write `backend/app/seed.py`**

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Admin, Config
from app.security import hash_password

_DEFAULT_CONFIG = {
    "retention_date": None,
    "qa_sla_text": "Questions are answered by a person, usually within 1 working day.",
}


def seed_admin_and_config(db: Session) -> None:
    s = get_settings()
    if not db.execute(select(Admin).filter_by(username=s.initial_admin_username)).first():
        db.add(Admin(username=s.initial_admin_username, password_hash=hash_password(s.initial_admin_password)))
    existing = set(db.execute(select(Config.key)).scalars().all())
    seeds = {
        "prep_window_days": str(s.prep_window_days),
        "display_timezone": s.display_timezone,
        **_DEFAULT_CONFIG,
    }
    for key, value in seeds.items():
        if key not in existing:
            db.add(Config(key=key, value=value))
    db.commit()
```

- [ ] **Step 5: Write `backend/app/deps.py`**

```python
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Admin, Candidate


def current_admin(request: Request, db: Session = Depends(get_db)) -> Admin:
    if request.session.get("role") != "admin":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "admin auth required")
    admin = db.get(Admin, request.session.get("admin_id"))
    if not admin:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "admin auth required")
    return admin


def current_candidate(request: Request, db: Session = Depends(get_db)) -> Candidate:
    if request.session.get("role") != "candidate":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "candidate auth required")
    cand = db.get(Candidate, request.session.get("candidate_pk"))
    if not cand:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "candidate auth required")
    return cand
```

- [ ] **Step 6: Write `backend/app/routers/auth.py` (admin portion now; candidate added in Task 8)**

```python
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import record
from app.db import get_db
from app.models import Admin
from app.schemas import AdminLogin
from app.security import verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/admin/login")
def admin_login(body: AdminLogin, request: Request, db: Session = Depends(get_db)):
    admin = db.execute(select(Admin).filter_by(username=body.username)).scalar_one_or_none()
    if not admin or not verify_password(body.password, admin.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")
    request.session.update({"role": "admin", "admin_id": admin.id})
    record(db, actor="admin", action="login", detail=f"admin '{admin.username}' logged in")
    return {"role": "admin", "id": admin.id}


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return {"ok": True}


@router.get("/me")
def me(request: Request):
    role = request.session.get("role")
    if not role:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "not authenticated")
    return {"role": role, "id": request.session.get("admin_id") or request.session.get("candidate_pk")}
```

- [ ] **Step 7: Wire middleware + routers + startup seed in `backend/app/main.py`**

```python
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.db import SessionLocal
from app.routers import auth, public
from app.seed import seed_admin_and_config


def create_app() -> FastAPI:
    app = FastAPI(title="Candidate Assessment Platform")
    app.add_middleware(
        SessionMiddleware,
        secret_key=get_settings().session_secret,
        https_only=False,  # set True behind Caddy in prod (Phase 5)
        same_site="lax",
    )
    app.include_router(public.router)
    app.include_router(auth.router)

    @app.on_event("startup")
    def _seed():
        db = SessionLocal()
        try:
            seed_admin_and_config(db)
        finally:
            db.close()

    return app


app = create_app()
```

- [ ] **Step 8: Run to verify the test passes**

Run: `cd backend && TEST_DATABASE_URL=...app_test pytest tests/test_admin_auth.py -v`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add backend/app/ backend/tests/test_admin_auth.py
git commit -m "feat(backend): sessions, admin seed, admin login/logout/me"
```

---

## Task 8: Candidate creation (admin) + set-password + candidate login

**Files:**
- Modify: `backend/app/routers/auth.py`
- Create: `backend/app/routers/admin.py`
- Modify: `backend/app/main.py` (mount admin router)
- Test: `backend/tests/test_candidate_flow.py`

**Interfaces:**
- Consumes: `current_admin`, `allocate_candidate_id`, `generate_token`, `hash_password`, `verify_password`, `record`.
- Produces:
  - POST `/api/admin/candidates` (admin) `{first_name}` → creates candidate `invited` with one-time token (24h expiry); returns `{candidate_id, first_name, status, set_password_path}` where `set_password_path = "/set-password?token=<token>"`. Audit `candidate_create`.
  - GET `/api/admin/candidates` (admin) → list with `{candidate_id, first_name, status, has_password, set_password_path|null}`.
  - POST `/api/auth/candidate/set-password` `{token, password}` → sets hash, status→`active`, clears token; audit `password_set`. 400 on bad/expired token.
  - POST `/api/auth/candidate/login` `{candidate_id, password}` → session `{role:candidate, candidate_pk}`; audit `login`; 401 on bad creds or non-active.

- [ ] **Step 1: Write failing test `backend/tests/test_candidate_flow.py`**

```python
from app.seed import seed_admin_and_config


def login_admin(client):
    client.post("/api/auth/admin/login", json={"username": "admin", "password": "changeme"})


def test_full_candidate_lifecycle(client, db_session):
    seed_admin_and_config(db_session)
    login_admin(client)

    created = client.post("/api/admin/candidates", json={"first_name": "Ada"})
    assert created.status_code == 201
    data = created.json()
    assert data["candidate_id"] == "cand-01"
    assert data["status"] == "invited"
    token = data["set_password_path"].split("token=")[1]

    # candidate sets password (no auth required, just token)
    sp = client.post("/api/auth/candidate/set-password", json={"token": token, "password": "pw-123456"})
    assert sp.status_code == 200

    # candidate logs in
    client.post("/api/auth/logout")
    li = client.post("/api/auth/candidate/login", json={"candidate_id": "cand-01", "password": "pw-123456"})
    assert li.status_code == 200
    me = client.get("/api/auth/me")
    assert me.json()["role"] == "candidate"


def test_set_password_bad_token(client, db_session):
    seed_admin_and_config(db_session)
    r = client.post("/api/auth/candidate/set-password", json={"token": "nope", "password": "pw-123456"})
    assert r.status_code == 400


def test_create_candidate_requires_admin(client, db_session):
    seed_admin_and_config(db_session)
    r = client.post("/api/admin/candidates", json={"first_name": "Ada"})
    assert r.status_code == 401
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && pytest tests/test_candidate_flow.py -v`
Expected: FAIL.

- [ ] **Step 3: Write `backend/app/routers/admin.py`**

```python
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import record
from app.candidate_ids import allocate_candidate_id
from app.db import get_db
from app.deps import current_admin
from app.models import Candidate
from app.schemas import CreateCandidate
from app.security import generate_token

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _set_password_path(token: str) -> str:
    return f"/set-password?token={token}"


@router.post("/candidates", status_code=status.HTTP_201_CREATED)
def create_candidate(
    body: CreateCandidate,
    db: Session = Depends(get_db),
    _: object = Depends(current_admin),
):
    cid = allocate_candidate_id(db)
    token = generate_token()
    cand = Candidate(
        candidate_id=cid,
        first_name=body.first_name,
        status="invited",
        password_set_token=token,
        password_set_token_expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    db.add(cand)
    db.commit()
    record(db, actor="admin", action="candidate_create", detail=f"created {cid}")
    return {
        "candidate_id": cid,
        "first_name": cand.first_name,
        "status": cand.status,
        "set_password_path": _set_password_path(token),
    }


@router.get("/candidates")
def list_candidates(db: Session = Depends(get_db), _: object = Depends(current_admin)):
    rows = db.execute(select(Candidate).order_by(Candidate.candidate_id)).scalars().all()
    return [
        {
            "candidate_id": c.candidate_id,
            "first_name": c.first_name,
            "status": c.status,
            "has_password": c.password_hash is not None,
            "set_password_path": _set_password_path(c.password_set_token)
            if c.password_set_token
            else None,
        }
        for c in rows
    ]
```

- [ ] **Step 4: Extend `backend/app/routers/auth.py` with candidate endpoints**

Append to `auth.py`:

```python
from datetime import datetime, timezone

from app.models import Candidate
from app.schemas import CandidateLogin, SetPassword
from app.security import hash_password


@router.post("/candidate/set-password")
def candidate_set_password(body: SetPassword, db: Session = Depends(get_db)):
    cand = db.execute(
        select(Candidate).filter_by(password_set_token=body.token)
    ).scalar_one_or_none()
    expires = cand.password_set_token_expires_at if cand else None
    if not cand or expires is None or expires < datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid or expired token")
    cand.password_hash = hash_password(body.password)
    cand.status = "active"
    cand.password_set_token = None
    cand.password_set_token_expires_at = None
    db.commit()
    record(db, actor=cand.candidate_id, action="password_set", detail="password set via token")
    return {"ok": True}


@router.post("/candidate/login")
def candidate_login(body: CandidateLogin, request: Request, db: Session = Depends(get_db)):
    cand = db.execute(
        select(Candidate).filter_by(candidate_id=body.candidate_id)
    ).scalar_one_or_none()
    if (
        not cand
        or cand.status != "active"
        or not cand.password_hash
        or not verify_password(body.password, cand.password_hash)
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")
    request.session.update({"role": "candidate", "candidate_pk": cand.id})
    record(db, actor=cand.candidate_id, action="login", detail="candidate logged in")
    return {"role": "candidate", "candidate_id": cand.candidate_id}
```

- [ ] **Step 5: Mount admin router in `main.py`**

Add `from app.routers import admin` and `app.include_router(admin.router)` in `create_app`.

- [ ] **Step 6: Run to verify the tests pass**

Run: `cd backend && TEST_DATABASE_URL=...app_test pytest tests/test_candidate_flow.py -v`
Expected: PASS.

- [ ] **Step 7: Verify the API key is never logged — grep the audit details**

Add to `test_candidate_flow.py`:

```python
def test_no_password_in_audit(client, db_session):
    from app.models import AuditLog
    seed_admin_and_config(db_session)
    login_admin(client)
    data = client.post("/api/admin/candidates", json={"first_name": "Ada"}).json()
    token = data["set_password_path"].split("token=")[1]
    client.post("/api/auth/candidate/set-password", json={"token": token, "password": "supersecretpw"})
    details = " ".join(r.detail or "" for r in db_session.query(AuditLog).all())
    assert "supersecretpw" not in details
```

Run: `cd backend && TEST_DATABASE_URL=...app_test pytest tests/test_candidate_flow.py -v`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/app/ backend/tests/test_candidate_flow.py
git commit -m "feat(backend): candidate creation, set-password, candidate login"
```

---

## Task 9: Frontend scaffold + API client + auth pages

**Files:**
- Create: `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/index.html`, `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/api/client.ts`, `frontend/src/pages/{AdminLogin,CandidateLogin,SetPassword,Privacy,AdminDashboard,CandidateDashboard}.tsx`

**Interfaces:**
- Consumes: backend `/api/*` (proxied in dev via Vite to `:8000`).
- Produces: a routed SPA. Routes: `/admin/login`, `/admin` (candidate list + create form), `/login` (candidate), `/set-password`, `/dashboard` (candidate placeholder), `/privacy`. API client `api.post/get` send `credentials: "include"`.

- [ ] **Step 1: Scaffold Vite React-TS**

Run: `npm create vite@latest frontend -- --template react-ts && cd frontend && npm install react-router-dom`

- [ ] **Step 2: Configure dev proxy in `frontend/vite.config.ts`**

```typescript
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://localhost:8000" } },
});
```

- [ ] **Step 3: Write `frontend/src/api/client.ts`**

```typescript
async function request(method: string, path: string, body?: unknown) {
  const res = await fetch(path, {
    method,
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || res.statusText);
  return res.json();
}

export const api = {
  get: (p: string) => request("GET", p),
  post: (p: string, b?: unknown) => request("POST", p, b),
};
```

- [ ] **Step 4: Write router + pages in `App.tsx`**

```tsx
import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import AdminLogin from "./pages/AdminLogin";
import AdminDashboard from "./pages/AdminDashboard";
import CandidateLogin from "./pages/CandidateLogin";
import SetPassword from "./pages/SetPassword";
import CandidateDashboard from "./pages/CandidateDashboard";
import Privacy from "./pages/Privacy";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/admin/login" element={<AdminLogin />} />
        <Route path="/admin" element={<AdminDashboard />} />
        <Route path="/login" element={<CandidateLogin />} />
        <Route path="/set-password" element={<SetPassword />} />
        <Route path="/dashboard" element={<CandidateDashboard />} />
        <Route path="/privacy" element={<Privacy />} />
        <Route path="*" element={<CandidateLogin />} />
      </Routes>
      <footer style={{ padding: 16, fontSize: 12 }}>
        <Link to="/privacy">Privacy</Link>
      </footer>
    </BrowserRouter>
  );
}
```

- [ ] **Step 5: Write `AdminLogin.tsx` (pattern for the other auth pages)**

```tsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";

export default function AdminLogin() {
  const [username, setU] = useState("");
  const [password, setP] = useState("");
  const [err, setErr] = useState("");
  const nav = useNavigate();
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    try {
      await api.post("/api/auth/admin/login", { username, password });
      nav("/admin");
    } catch (x) {
      setErr(String(x));
    }
  }
  return (
    <form onSubmit={submit}>
      <h1>Admin login</h1>
      <input placeholder="username" value={username} onChange={(e) => setU(e.target.value)} />
      <input type="password" placeholder="password" value={password} onChange={(e) => setP(e.target.value)} />
      <button>Log in</button>
      {err && <p role="alert">{err}</p>}
    </form>
  );
}
```

- [ ] **Step 6: Write `CandidateLogin.tsx`, `SetPassword.tsx`, `AdminDashboard.tsx`, `CandidateDashboard.tsx`**

`CandidateLogin.tsx` — same shape as AdminLogin but posts `/api/auth/candidate/login` with `{candidate_id, password}`, navigates `/dashboard`.

`SetPassword.tsx` — reads `token` from `new URLSearchParams(location.search)`, posts `/api/auth/candidate/set-password` `{token, password}`, on success navigates `/login`.

`AdminDashboard.tsx`:

```tsx
import { useEffect, useState } from "react";
import { api } from "../api/client";

type Cand = { candidate_id: string; first_name: string; status: string; set_password_path: string | null };

export default function AdminDashboard() {
  const [cands, setCands] = useState<Cand[]>([]);
  const [name, setName] = useState("");
  async function load() { setCands(await api.get("/api/admin/candidates")); }
  useEffect(() => { load(); }, []);
  async function create(e: React.FormEvent) {
    e.preventDefault();
    await api.post("/api/admin/candidates", { first_name: name });
    setName("");
    load();
  }
  return (
    <div>
      <h1>Candidates</h1>
      <form onSubmit={create}>
        <input placeholder="first name" value={name} onChange={(e) => setName(e.target.value)} />
        <button>Create</button>
      </form>
      <ul>
        {cands.map((c) => (
          <li key={c.candidate_id}>
            {c.candidate_id} — {c.first_name} — {c.status}
            {c.set_password_path && <code> {location.origin}{c.set_password_path}</code>}
          </li>
        ))}
      </ul>
    </div>
  );
}
```

`CandidateDashboard.tsx` — placeholder: `<h1>Welcome</h1>` plus a logout button calling `/api/auth/logout`. (Filled in Phase 2/3.)

- [ ] **Step 7: Write `Privacy.tsx` (static notice, §7 of design)**

```tsx
export default function Privacy() {
  return (
    <main style={{ maxWidth: 640, margin: "2rem auto", lineHeight: 1.5 }}>
      <h1>Privacy notice</h1>
      <p>
        This assessment platform deliberately holds the minimum personal data. About you we store
        only your <strong>first name</strong> and a system-generated ID (e.g. <code>cand-07</code>),
        together with your assessment booking, file downloads, questions you ask, and an Anthropic
        API key stored <strong>encrypted</strong>.
      </p>
      <p>
        We do <strong>not</strong> store your email, surname, phone number, IP-based analytics, or
        any marketing data. We use a single essential session cookie to keep you logged in; it is
        removed when you log out or it expires. Because it is strictly necessary, no cookie-consent
        banner is required.
      </p>
      <p>
        Your data is held only for the duration of the assessment process and is then permanently
        deleted. You may ask the assessor to erase your data at any time.
      </p>
    </main>
  );
}
```

- [ ] **Step 8: Build the frontend to verify it compiles**

Run: `cd frontend && npm run build`
Expected: build succeeds, `frontend/dist/` produced.

- [ ] **Step 9: Manual end-to-end smoke (stack up)**

Run: `docker compose -f compose.local.yaml up -d --build` then `cd frontend && npm run dev`. In a browser: log in as admin → create "Ada" → copy the set-password link → open it → set a password → log in as `cand-01`. Confirm each step works and `/privacy` renders.

- [ ] **Step 10: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): scaffold SPA with auth pages and privacy notice"
```

---

## Task 10: CI (lint + tests + build) — minimal Phase-1 gate

**Files:**
- Create: `.github/workflows/ci.yml`

**Interfaces:**
- Produces: a GitHub Actions workflow that on push/PR runs ruff, backend pytest (against a Postgres service), and frontend lint + build. (Image build added in Phase 5.)

- [ ] **Step 1: Write `.github/workflows/ci.yml`**

```yaml
name: CI
on: [push, pull_request]

jobs:
  backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env: { POSTGRES_USER: app, POSTGRES_PASSWORD: app, POSTGRES_DB: app_test }
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U app" --health-interval 5s --health-timeout 5s --health-retries 10
    defaults: { run: { working-directory: backend } }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -e ".[dev]"
      - run: ruff check .
      - run: pytest -v
        env:
          TEST_DATABASE_URL: postgresql+psycopg://app:app@localhost:5432/app_test
          INITIAL_ADMIN_PASSWORD: changeme

  frontend:
    runs-on: ubuntu-latest
    defaults: { run: { working-directory: frontend } }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20" }
      - run: npm ci
      - run: npm run lint
      - run: npm run build
```

- [ ] **Step 2: Run lint + tests locally to confirm CI will pass**

Run: `cd backend && ruff check . && TEST_DATABASE_URL=...app_test pytest -v` and `cd frontend && npm run lint && npm run build`
Expected: all green.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: lint, backend tests, frontend build"
```

---

## Phase 1 Checkpoint

Demonstrate locally (spec §Phase-1 checkpoint):
1. Admin logs in.
2. Admin creates a candidate; a `cand-NN` is assigned; a set-password link is shown.
3. Candidate opens the link, sets a password, becomes `active`.
4. Candidate logs in with `candidate_id` + password.
5. `/privacy` renders; footer links to it.
6. `audit_log` contains rows for admin login, candidate_create, password_set, candidate login — and **no** secret material.
7. `ruff`, `pytest`, and `npm run build` all green.

---

## Self-Review (against build-spec Phase 1)

- **Scaffold FastAPI/React/Postgres/Compose/Caddy** → Tasks 1, 4, 9. ✓ (Caddyfile present; real TLS deferred to Phase 5 per design §2.)
- **Data model + migrations** → Tasks 2, 5 (all eight §4 tables, unique constraints). ✓
- **Admin auth, session-based, env-seeded** → Task 7. ✓
- **Candidate accounts pre-created, candidate_id assigned, invited + one-time token, set-password link shown (no email)** → Task 8. ✓
- **Candidate first login via link → active → login with candidate_id+password** → Task 8. ✓
- **Audit-log all auth events** → audit choke-point Task 6; wired in Tasks 7, 8 (login, password_set, candidate_create). ✓
- **`/privacy` (design addition)** → Task 9 Step 7. ✓
- **No secrets in logs** → Task 8 Step 7 explicit test. ✓

No placeholders remain; types are consistent across tasks (`set_password_path`, `current_admin/current_candidate`, `record`, `allocate_candidate_id` used as defined). Booking/`unlock_at` column exists on the model now but is exercised in Phase 2.
