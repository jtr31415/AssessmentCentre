"""Tests for GET /api/admin/activity — admin monitoring view.

Uses shared db_session + client fixtures from conftest. DO NOT define a local engine.

Download columns are now driven by the DB-backed content library (``content_file``)
rather than a hard-coded manifest, so each test that inspects ``downloads`` seeds
its own content rows first.
"""

from datetime import UTC, datetime

from app.models import AuditLog, Booking, Candidate, ContentFile, DownloadEvent, Question, Slot
from app.seed import seed_admin_and_config

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def login_admin(client):
    client.post("/api/auth/admin/login", json={"username": "admin", "password": "changeme"})


def _seed_content_files(db_session) -> list[str]:
    """Insert two content_file rows; return their file_keys (ordered)."""
    keys = ["key_brief_0001", "key_data_0002"]
    db_session.add(
        ContentFile(
            file_key=keys[0],
            label="Exercise Brief",
            category="brief",
            original_filename="brief.pdf",
            stored_filename=f"{keys[0]}.pdf",
            media_type="application/pdf",
            size_bytes=10,
            sort_order=0,
        )
    )
    db_session.add(
        ContentFile(
            file_key=keys[1],
            label="Turbine Data",
            category="data",
            original_filename="turbine.csv",
            stored_filename=f"{keys[1]}.csv",
            media_type="text/csv",
            size_bytes=10,
            sort_order=1,
        )
    )
    db_session.commit()
    return keys


def _seed_active_candidate(db_session, first_download_key: str) -> Candidate:
    """Seed an active candidate with booking, audit logs, a download, and questions."""
    cand = Candidate(
        candidate_id="C001",
        first_name="Alice",
        status="active",
    )
    db_session.add(cand)
    db_session.flush()

    slot = Slot(starts_at=datetime(2026, 7, 1, 9, 0, tzinfo=UTC))
    db_session.add(slot)
    db_session.flush()

    unlock = datetime(2026, 7, 1, 8, 30, tzinfo=UTC)
    booking = Booking(candidate_id=cand.id, slot_id=slot.id, unlock_at=unlock)
    db_session.add(booking)

    db_session.add(AuditLog(actor="C001", action="login"))
    db_session.add(AuditLog(actor="C001", action="api_key_reveal"))

    db_session.add(DownloadEvent(candidate_id=cand.id, file_key=first_download_key))

    db_session.add(Question(candidate_id=cand.id, body="Question one"))
    db_session.add(Question(candidate_id=cand.id, body="Question two"))

    db_session.commit()
    return cand


def _seed_invited_candidate(db_session) -> Candidate:
    """Seed a plain invited candidate with no activity."""
    cand = Candidate(
        candidate_id="C002",
        first_name="Bob",
        status="invited",
    )
    db_session.add(cand)
    db_session.commit()
    return cand


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_activity_active_candidate_full_row(client, db_session):
    """An active candidate with all activity shows all fields populated."""
    seed_admin_and_config(db_session)
    keys = _seed_content_files(db_session)
    _seed_active_candidate(db_session, keys[0])
    login_admin(client)

    r = client.get("/api/admin/activity")
    assert r.status_code == 200, r.text
    rows = r.json()

    row = next((x for x in rows if x["candidate_id"] == "C001"), None)
    assert row is not None, "Expected row for C001"

    assert row["first_name"] == "Alice"
    assert row["status"] == "active"
    assert row["has_booking"] is True
    assert row["slot_starts_at"] is not None
    assert row["unlock_at"] is not None
    assert row["has_logged_in"] is True
    assert row["key_revealed"] is True
    assert row["question_count"] == 2

    # downloads: first key has a timestamp, the other null
    assert row["downloads"][keys[0]] is not None, f"{keys[0]} should have a timestamp"
    assert row["downloads"][keys[1]] is None, f"{keys[1]} should be null"

    # All current content keys present
    for key in keys:
        assert key in row["downloads"], f"Missing content key: {key}"


def test_activity_invited_candidate_empty_row(client, db_session):
    """A fresh invited candidate with no activity shows all-false/null/zero."""
    seed_admin_and_config(db_session)
    keys = _seed_content_files(db_session)
    _seed_invited_candidate(db_session)
    login_admin(client)

    r = client.get("/api/admin/activity")
    assert r.status_code == 200, r.text
    rows = r.json()

    row = next((x for x in rows if x["candidate_id"] == "C002"), None)
    assert row is not None, "Expected row for C002"

    assert row["first_name"] == "Bob"
    assert row["status"] == "invited"
    assert row["has_booking"] is False
    assert row["slot_starts_at"] is None
    assert row["unlock_at"] is None
    assert row["has_logged_in"] is False
    assert row["key_revealed"] is False
    assert row["question_count"] == 0

    for key in keys:
        assert key in row["downloads"]
        assert row["downloads"][key] is None, f"{key} should be null for fresh candidate"


def test_activity_ordered_by_candidate_id(client, db_session):
    """Response rows are ordered ascending by candidate_id."""
    seed_admin_and_config(db_session)
    keys = _seed_content_files(db_session)
    _seed_active_candidate(db_session, keys[0])   # C001
    _seed_invited_candidate(db_session)  # C002
    login_admin(client)

    r = client.get("/api/admin/activity")
    assert r.status_code == 200, r.text
    rows = r.json()

    cids = [row["candidate_id"] for row in rows]
    assert "C001" in cids
    assert "C002" in cids
    assert cids == sorted(cids), f"Expected ascending order, got {cids}"


def test_activity_includes_every_candidate(client, db_session):
    """All seeded candidates appear in the activity list."""
    seed_admin_and_config(db_session)
    keys = _seed_content_files(db_session)
    _seed_active_candidate(db_session, keys[0])   # C001
    _seed_invited_candidate(db_session)  # C002
    login_admin(client)

    r = client.get("/api/admin/activity")
    assert r.status_code == 200, r.text
    rows = r.json()

    cids = {row["candidate_id"] for row in rows}
    assert "C001" in cids
    assert "C002" in cids


def test_activity_admin_only(client, db_session):
    """Non-admin (unauthenticated) request → 401."""
    seed_admin_and_config(db_session)

    r = client.get("/api/admin/activity")
    assert r.status_code == 401, r.text
