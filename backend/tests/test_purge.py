"""Tests for POST /api/admin/purge — right to erasure (GDPR Art.17).

Written BEFORE implementation (TDD / RED-first).
Uses shared db_session / client fixtures from conftest.py.
"""

import os

os.environ.setdefault("INITIAL_ADMIN_PASSWORD", "changeme")

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.models import Admin, AuditLog, Booking, Candidate, Config, DownloadEvent, Question, Slot
from app.seed import seed_admin_and_config

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CONFIRM_PHRASE = "PURGE ALL CANDIDATE DATA"


def login_admin(client):
    r = client.post("/api/auth/admin/login", json={"username": "admin", "password": "changeme"})
    assert r.status_code == 200, r.text


def _create_slot(db_session) -> int:
    slot = Slot(starts_at=datetime.now(UTC) + timedelta(days=30), capacity=10)
    db_session.add(slot)
    db_session.flush()
    return slot.id


def _seed_candidates_with_data(db_session, slot_id: int) -> list[str]:
    """
    Insert 2 candidates each with:
      - a Booking (pointing to slot_id)
      - a Question
      - a DownloadEvent
      - a candidate-actor AuditLog row (action="login")
    Returns list of candidate_id strings.
    """
    cids = []
    for i in range(1, 3):
        cid_str = f"cand-purge-{i:02d}"
        cand = Candidate(
            candidate_id=cid_str,
            first_name=f"Purge{i}",
            status="active",
        )
        db_session.add(cand)
        db_session.flush()

        booking = Booking(
            candidate_id=cand.id,
            slot_id=slot_id,
            unlock_at=datetime.now(UTC),
        )
        db_session.add(booking)

        question = Question(candidate_id=cand.id, body="What is X?")
        db_session.add(question)

        dl = DownloadEvent(candidate_id=cand.id, file_key="exercise_brief.pdf")
        db_session.add(dl)

        # Candidate-attributable audit row
        db_session.add(AuditLog(actor=cid_str, action="login"))

        cids.append(cid_str)

    db_session.commit()
    return cids


def _insert_admin_audit_row(db_session) -> int:
    row = AuditLog(actor="admin", action="candidate_create", detail="created cand-purge-00")
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row.id


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPurgeWrongConfirm:
    """Wrong / empty confirm phrase → 400 and nothing deleted."""

    def _count(self, db_session, model):
        return db_session.query(model).count()

    def _setup(self, client, db_session):
        seed_admin_and_config(db_session)
        slot_id = _create_slot(db_session)
        _seed_candidates_with_data(db_session, slot_id)
        _insert_admin_audit_row(db_session)
        login_admin(client)

    def test_wrong_confirm_returns_400(self, client, db_session):
        self._setup(client, db_session)
        r = client.post("/api/admin/purge", json={"confirm": "nope"})
        assert r.status_code == 400
        assert "confirmation phrase did not match" in r.json()["detail"]

    def test_empty_confirm_returns_400(self, client, db_session):
        self._setup(client, db_session)
        r = client.post("/api/admin/purge", json={"confirm": ""})
        assert r.status_code == 400

    def test_wrong_confirm_deletes_nothing(self, client, db_session):
        self._setup(client, db_session)
        before_candidates = self._count(db_session, Candidate)
        before_bookings = self._count(db_session, Booking)
        before_questions = self._count(db_session, Question)
        before_downloads = self._count(db_session, DownloadEvent)

        client.post("/api/admin/purge", json={"confirm": "nope"})

        # Refresh counts
        db_session.expire_all()
        assert self._count(db_session, Candidate) == before_candidates
        assert self._count(db_session, Booking) == before_bookings
        assert self._count(db_session, Question) == before_questions
        assert self._count(db_session, DownloadEvent) == before_downloads

    def test_almost_correct_confirm_returns_400(self, client, db_session):
        """Lowercase / trailing space must not be accepted."""
        self._setup(client, db_session)
        r = client.post("/api/admin/purge", json={"confirm": "purge all candidate data"})
        assert r.status_code == 400


class TestPurgeCorrectConfirm:
    """Correct phrase → 200, data purged, admin / config / admin-audit preserved."""

    def _setup(self, client, db_session):
        seed_admin_and_config(db_session)
        slot_id = _create_slot(db_session)
        _seed_candidates_with_data(db_session, slot_id)
        admin_audit_id = _insert_admin_audit_row(db_session)
        login_admin(client)
        return admin_audit_id

    def test_returns_200(self, client, db_session):
        self._setup(client, db_session)
        r = client.post("/api/admin/purge", json={"confirm": CONFIRM_PHRASE})
        assert r.status_code == 200, r.text

    def test_candidate_table_is_empty(self, client, db_session):
        self._setup(client, db_session)
        client.post("/api/admin/purge", json={"confirm": CONFIRM_PHRASE})
        db_session.expire_all()
        assert db_session.query(Candidate).count() == 0

    def test_booking_table_is_empty(self, client, db_session):
        self._setup(client, db_session)
        client.post("/api/admin/purge", json={"confirm": CONFIRM_PHRASE})
        db_session.expire_all()
        assert db_session.query(Booking).count() == 0

    def test_question_table_is_empty(self, client, db_session):
        self._setup(client, db_session)
        client.post("/api/admin/purge", json={"confirm": CONFIRM_PHRASE})
        db_session.expire_all()
        assert db_session.query(Question).count() == 0

    def test_download_event_table_is_empty(self, client, db_session):
        self._setup(client, db_session)
        client.post("/api/admin/purge", json={"confirm": CONFIRM_PHRASE})
        db_session.expire_all()
        assert db_session.query(DownloadEvent).count() == 0

    def test_candidate_actor_audit_rows_are_gone(self, client, db_session):
        self._setup(client, db_session)
        client.post("/api/admin/purge", json={"confirm": CONFIRM_PHRASE})
        db_session.expire_all()
        remaining = (
            db_session.query(AuditLog).filter(AuditLog.actor != "admin").count()
        )
        assert remaining == 0

    def test_admin_audit_rows_are_preserved(self, client, db_session):
        admin_audit_id = self._setup(client, db_session)
        client.post("/api/admin/purge", json={"confirm": CONFIRM_PHRASE})
        db_session.expire_all()
        row = db_session.get(AuditLog, admin_audit_id)
        assert row is not None, "Pre-existing admin-actor audit row must survive purge"

    def test_admin_account_is_preserved(self, client, db_session):
        self._setup(client, db_session)
        client.post("/api/admin/purge", json={"confirm": CONFIRM_PHRASE})
        db_session.expire_all()
        assert db_session.query(Admin).count() >= 1

    def test_config_rows_are_preserved(self, client, db_session):
        self._setup(client, db_session)
        before = db_session.query(Config).count()
        client.post("/api/admin/purge", json={"confirm": CONFIRM_PHRASE})
        db_session.expire_all()
        assert db_session.query(Config).count() == before

    def test_data_purge_audit_row_is_created(self, client, db_session):
        self._setup(client, db_session)
        client.post("/api/admin/purge", json={"confirm": CONFIRM_PHRASE})
        db_session.expire_all()
        purge_row = db_session.execute(
            select(AuditLog).where(
                AuditLog.actor == "admin",
                AuditLog.action == "data_purge",
            )
        ).scalar_one_or_none()
        assert purge_row is not None, "A data_purge audit row (actor=admin) must be created"

    def test_response_deleted_counts_correct(self, client, db_session):
        self._setup(client, db_session)
        r = client.post("/api/admin/purge", json={"confirm": CONFIRM_PHRASE})
        assert r.status_code == 200, r.text
        data = r.json()
        deleted = data["deleted"]
        assert deleted["candidates"] == 2
        assert deleted["bookings"] == 2
        assert deleted["questions"] == 2
        assert deleted["download_events"] == 2
        # 2 candidate-actor audit rows (login×2) were inserted
        assert deleted["audit_rows"] == 2

    def test_response_has_deleted_key(self, client, db_session):
        self._setup(client, db_session)
        r = client.post("/api/admin/purge", json={"confirm": CONFIRM_PHRASE})
        assert "deleted" in r.json()
        for key in ("candidates", "bookings", "questions", "download_events", "audit_rows"):
            assert key in r.json()["deleted"]


class TestPurgeAdminOnly:
    """Endpoint must be admin-gated."""

    def test_unauthenticated_returns_401(self, client, db_session):
        seed_admin_and_config(db_session)
        r = client.post("/api/admin/purge", json={"confirm": CONFIRM_PHRASE})
        assert r.status_code == 401

    def test_non_admin_session_returns_401_and_deletes_nothing(self, client, db_session):
        """A candidate session must not be able to trigger the purge."""
        seed_admin_and_config(db_session)

        # Create a candidate via admin API first (uses integer-based candidate_id: cand-01)
        login_admin(client)
        created = client.post("/api/admin/candidates", json={"first_name": "Hacker"})
        assert created.status_code == 201, created.text
        cand_id_str = created.json()["candidate_id"]
        token = created.json()["set_password_path"].split("token=")[1]
        client.post(
            "/api/auth/candidate/set-password",
            json={"token": token, "password": "pw-123456"},
        )
        client.post("/api/auth/logout")
        li = client.post(
            "/api/auth/candidate/login",
            json={"candidate_id": cand_id_str, "password": "pw-123456"},
        )
        assert li.status_code == 200

        before_count = db_session.query(Candidate).count()
        r = client.post("/api/admin/purge", json={"confirm": CONFIRM_PHRASE})
        assert r.status_code == 401

        db_session.expire_all()
        assert db_session.query(Candidate).count() == before_count, (
            "Candidate count must not change after a rejected purge attempt"
        )
