"""Tests for admin API-key paste (encrypted) and gated candidate key reveal.

TDD: written BEFORE implementation (RED first).

Uses the shared ``db_session``/``client`` fixtures from conftest.py.
Do NOT define a local ``engine`` fixture — that would drop tables on teardown
and corrupt the shared test DB (see project CRITICAL rule).

Mirrors patterns from test_content.py / test_candidate_flow.py.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.models import AuditLog, Booking, Candidate
from app.security import decrypt_secret
from app.seed import seed_admin_and_config

# ---------------------------------------------------------------------------
# Helpers (mirrors test_content.py pattern exactly)
# ---------------------------------------------------------------------------

_CANDIDATE_PASSWORD = "pw-apikey1"


def login_admin(client):
    client.post("/api/auth/admin/login", json={"username": "admin", "password": "changeme"})


def create_and_activate_candidate(client, db_session):
    """Seed admin, create a candidate, set password, log in. Returns candidate_id str."""
    seed_admin_and_config(db_session)
    login_admin(client)

    created = client.post("/api/admin/candidates", json={"first_name": "KeyTester"})
    assert created.status_code == 201
    data = created.json()
    token = data["set_password_path"].split("token=")[1]

    client.post(
        "/api/auth/candidate/set-password",
        json={"token": token, "password": _CANDIDATE_PASSWORD},
    )
    client.post("/api/auth/logout")
    li = client.post(
        "/api/auth/candidate/login",
        json={"candidate_id": data["candidate_id"], "password": _CANDIDATE_PASSWORD},
    )
    assert li.status_code == 200
    client.post("/api/me/nda/accept")  # accept NDA at first login (gates participation)
    return data["candidate_id"]


def make_candidate_unlocked(client, db_session, candidate_id: str):
    """Give the candidate a booking with unlock_at in the past (mirrors test_content.py)."""
    client.post("/api/auth/logout")
    login_admin(client)
    future = datetime.now(UTC) + timedelta(hours=1)
    r = client.post(
        "/api/admin/slots",
        json={"starts_at": future.isoformat(), "capacity": 1},
    )
    assert r.status_code == 201, r.text
    slot_id = r.json()["id"]

    client.post("/api/auth/logout")
    li = client.post(
        "/api/auth/candidate/login",
        json={"candidate_id": candidate_id, "password": _CANDIDATE_PASSWORD},
    )
    assert li.status_code == 200

    r = client.post(f"/api/slots/{slot_id}/book")
    assert r.status_code == 201, r.text

    # Force unlock_at to the past so is_unlocked is definitely True
    cand_row = db_session.execute(
        select(Candidate).where(Candidate.candidate_id == candidate_id)
    ).scalar_one()
    booking = db_session.execute(
        select(Booking).where(Booking.candidate_id == cand_row.id)
    ).scalar_one()
    booking.unlock_at = datetime.now(UTC) - timedelta(hours=1)
    db_session.commit()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

_TEST_KEY = "sk-test-supersecret-api-key-12345"
_NOTE_FRAGMENT = "LLM features"  # part of the expected usage note


class TestAdminPasteKey:
    """Admin PUT /api/admin/candidates/{id}/api-key — stores encrypted, never plaintext."""

    def test_admin_paste_stores_encrypted_not_plaintext(self, client, db_session):
        """After paste, DB column api_key_encrypted differs from the plaintext key."""
        candidate_id = create_and_activate_candidate(client, db_session)
        client.post("/api/auth/logout")
        login_admin(client)

        r = client.put(
            f"/api/admin/candidates/{candidate_id}/api-key",
            json={"api_key": _TEST_KEY},
        )
        assert r.status_code == 200
        assert r.json() == {"ok": True}

        db_session.expire_all()
        cand = db_session.execute(
            select(Candidate).where(Candidate.candidate_id == candidate_id)
        ).scalar_one()
        assert cand.api_key_encrypted is not None
        assert cand.api_key_encrypted != _TEST_KEY, (
            "DB must NOT store the plaintext key"
        )
        assert decrypt_secret(cand.api_key_encrypted) == _TEST_KEY, (
            "decrypt_secret(stored) must recover the original key"
        )

    def test_admin_paste_is_admin_only(self, client, db_session):
        """Non-admin (unauthenticated) gets 401 on PUT /api/admin/candidates/{id}/api-key."""
        candidate_id = create_and_activate_candidate(client, db_session)
        # candidate is currently logged in — NOT admin
        r = client.put(
            f"/api/admin/candidates/{candidate_id}/api-key",
            json={"api_key": _TEST_KEY},
        )
        assert r.status_code == 401

    def test_admin_paste_unknown_candidate_returns_404(self, client, db_session):
        """PUT with an unknown candidate_id returns 404."""
        seed_admin_and_config(db_session)
        login_admin(client)
        r = client.put(
            "/api/admin/candidates/DOES-NOT-EXIST/api-key",
            json={"api_key": _TEST_KEY},
        )
        assert r.status_code == 404


class TestAdminDeleteKey:
    """Admin DELETE /api/admin/candidates/{id}/api-key — clears the stored key."""

    def test_admin_delete_clears_key(self, client, db_session):
        """After DELETE the api_key_encrypted column is None."""
        candidate_id = create_and_activate_candidate(client, db_session)
        client.post("/api/auth/logout")
        login_admin(client)

        # Paste first
        client.put(
            f"/api/admin/candidates/{candidate_id}/api-key",
            json={"api_key": _TEST_KEY},
        )

        # Then delete
        r = client.delete(f"/api/admin/candidates/{candidate_id}/api-key")
        assert r.status_code == 200
        assert r.json() == {"ok": True}

        db_session.expire_all()
        cand = db_session.execute(
            select(Candidate).where(Candidate.candidate_id == candidate_id)
        ).scalar_one()
        assert cand.api_key_encrypted is None


class TestCandidateRevealKey:
    """GET /api/me/api-key — unlock-gated reveal for candidates."""

    def test_locked_candidate_gets_403(self, client, db_session):
        """Candidate with no booking (locked) → 403 on GET /api/me/api-key."""
        create_and_activate_candidate(client, db_session)
        r = client.get("/api/me/api-key")
        assert r.status_code == 403

    def test_unlocked_candidate_gets_key_and_note(self, client, db_session):
        """Unlocked candidate with a set key → 200 with plaintext key + usage note."""
        candidate_id = create_and_activate_candidate(client, db_session)

        # Admin pastes the key
        client.post("/api/auth/logout")
        login_admin(client)
        client.put(
            f"/api/admin/candidates/{candidate_id}/api-key",
            json={"api_key": _TEST_KEY},
        )

        # Unlock the candidate
        make_candidate_unlocked(client, db_session, candidate_id)

        r = client.get("/api/me/api-key")
        assert r.status_code == 200
        data = r.json()
        assert data["api_key"] == _TEST_KEY
        assert _NOTE_FRAGMENT in data["note"]

    def test_reveal_writes_audit_row(self, client, db_session):
        """GET /api/me/api-key writes an audit row with action='api_key_reveal'."""
        candidate_id = create_and_activate_candidate(client, db_session)

        client.post("/api/auth/logout")
        login_admin(client)
        client.put(
            f"/api/admin/candidates/{candidate_id}/api-key",
            json={"api_key": _TEST_KEY},
        )
        make_candidate_unlocked(client, db_session, candidate_id)

        client.get("/api/me/api-key")

        db_session.expire_all()
        audit = db_session.execute(
            select(AuditLog).where(
                AuditLog.action == "api_key_reveal",
                AuditLog.actor == candidate_id,
            )
        ).scalar_one_or_none()
        assert audit is not None, "AuditLog row for api_key_reveal must be written"

    def test_reveal_with_no_key_set_returns_404(self, client, db_session):
        """Unlocked candidate with no key assigned → 404."""
        candidate_id = create_and_activate_candidate(client, db_session)
        make_candidate_unlocked(client, db_session, candidate_id)

        r = client.get("/api/me/api-key")
        assert r.status_code == 404
        assert "no API key assigned" in r.json()["detail"]

    def test_no_audit_row_contains_plaintext_key(self, client, db_session):
        """No audit_log detail row contains the plaintext key string (no-leak assertion)."""
        candidate_id = create_and_activate_candidate(client, db_session)

        # Admin pastes
        client.post("/api/auth/logout")
        login_admin(client)
        client.put(
            f"/api/admin/candidates/{candidate_id}/api-key",
            json={"api_key": _TEST_KEY},
        )
        make_candidate_unlocked(client, db_session, candidate_id)

        # Candidate reveals
        client.get("/api/me/api-key")

        # Inspect every audit row
        db_session.expire_all()
        all_rows = db_session.execute(select(AuditLog)).scalars().all()
        all_details = " ".join(r.detail for r in all_rows if r.detail)
        assert _TEST_KEY not in all_details, (
            "Plaintext API key must NEVER appear in any audit_log detail row"
        )
