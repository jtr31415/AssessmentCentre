"""Tests for gated content list and streamed file download.

TDD: written BEFORE implementation (RED first).

Uses the shared ``db_session`` fixture from conftest.py.  Do NOT define a
local ``engine`` fixture — a module-scoped engine that calls
``Base.metadata.drop_all`` on teardown corrupts the shared test DB for every
later module (see project CRITICAL rule).

Mirrors patterns from test_booking.py / test_candidate_flow.py.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.content_manifest import MANIFEST
from app.models import AuditLog, Booking, Candidate, DownloadEvent
from app.seed import seed_admin_and_config

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def login_admin(client):
    client.post("/api/auth/admin/login", json={"username": "admin", "password": "changeme"})


def create_and_activate_candidate(client, db_session):
    """Seed admin, create a candidate, set password, log in. Returns candidate_id str."""
    seed_admin_and_config(db_session)
    login_admin(client)

    created = client.post("/api/admin/candidates", json={"first_name": "ContentTester"})
    assert created.status_code == 201
    data = created.json()
    token = data["set_password_path"].split("token=")[1]

    client.post(
        "/api/auth/candidate/set-password",
        json={"token": token, "password": "pw-content1"},
    )
    client.post("/api/auth/logout")
    li = client.post(
        "/api/auth/candidate/login",
        json={"candidate_id": data["candidate_id"], "password": "pw-content1"},
    )
    assert li.status_code == 200
    return data["candidate_id"]


def make_candidate_unlocked(client, db_session, candidate_id: str):
    """Give the candidate a booking whose unlock_at is in the past.

    Strategy: create a slot 1 hour in the future (so unlock_at == now because
    the slot is within the 8-day prep window → compute_unlock_at returns now),
    book it via the API, then force unlock_at to 1 hour ago to guarantee
    is_unlocked() returns True regardless of minor timing jitter.
    """
    # Switch to admin to create a slot
    client.post("/api/auth/logout")
    login_admin(client)
    future = datetime.now(UTC) + timedelta(hours=1)
    r = client.post(
        "/api/admin/slots",
        json={"starts_at": future.isoformat(), "capacity": 1},
    )
    assert r.status_code == 201, r.text
    slot_id = r.json()["id"]

    # Switch back to candidate and book
    client.post("/api/auth/logout")
    li = client.post(
        "/api/auth/candidate/login",
        json={"candidate_id": candidate_id, "password": "pw-content1"},
    )
    assert li.status_code == 200

    r = client.post(f"/api/slots/{slot_id}/book")
    assert r.status_code == 201, r.text

    # Force unlock_at to the past in the DB so is_unlocked is definitely True
    cand_row = db_session.execute(
        select(Candidate).where(Candidate.candidate_id == candidate_id)
    ).scalar_one()
    booking = db_session.execute(
        select(Booking).where(Booking.candidate_id == cand_row.id)
    ).scalar_one()
    booking.unlock_at = datetime.now(UTC) - timedelta(hours=1)
    db_session.commit()


@pytest.fixture()
def content_dir(tmp_path):
    """Create placeholder files for every MANIFEST entry and return the dir path."""
    for entry in MANIFEST:
        (tmp_path / entry["filename"]).write_bytes(
            f"placeholder-content-for-{entry['file_key']}".encode()
        )
    return tmp_path


@pytest.fixture(autouse=False)
def patch_content_dir(content_dir, monkeypatch):
    """Override get_settings().content_dir to point at our tmp content dir."""
    from app.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "content_dir", str(content_dir))
    return content_dir


# ---------------------------------------------------------------------------
# Test classes
# ---------------------------------------------------------------------------


class TestContentListLocked:
    """Locked candidate (no booking OR future unlock) → 403 on GET /api/content."""

    def test_no_booking_gets_403_on_list(self, client, db_session, patch_content_dir):
        """Candidate without any booking is locked → 403 on GET /api/content."""
        create_and_activate_candidate(client, db_session)
        r = client.get("/api/content")
        assert r.status_code == 403

    def test_future_unlock_gets_403_on_list(self, client, db_session, patch_content_dir):
        """Candidate with a future unlock_at is still locked → 403 on GET /api/content."""
        candidate_id = create_and_activate_candidate(client, db_session)

        # Create a slot far in the future (unlock_at will also be far in the future)
        client.post("/api/auth/logout")
        login_admin(client)
        far_future = datetime.now(UTC) + timedelta(days=30)
        r = client.post(
            "/api/admin/slots",
            json={"starts_at": far_future.isoformat(), "capacity": 1},
        )
        assert r.status_code == 201
        slot_id = r.json()["id"]

        client.post("/api/auth/logout")
        client.post(
            "/api/auth/candidate/login",
            json={"candidate_id": candidate_id, "password": "pw-content1"},
        )
        client.post(f"/api/slots/{slot_id}/book")

        # unlock_at is still in the future → should be locked
        r = client.get("/api/content")
        assert r.status_code == 403


class TestContentDownloadLocked:
    """Locked candidate → 403 on GET /api/content/{file_key}."""

    def test_no_booking_gets_403_on_download(self, client, db_session, patch_content_dir):
        """Candidate without any booking is locked → 403 on download."""
        create_and_activate_candidate(client, db_session)
        file_key = MANIFEST[0]["file_key"]
        r = client.get(f"/api/content/{file_key}")
        assert r.status_code == 403

    def test_future_unlock_gets_403_on_download(self, client, db_session, patch_content_dir):
        """Candidate with a future unlock_at → 403 on download."""
        candidate_id = create_and_activate_candidate(client, db_session)

        client.post("/api/auth/logout")
        login_admin(client)
        far_future = datetime.now(UTC) + timedelta(days=30)
        r = client.post(
            "/api/admin/slots",
            json={"starts_at": far_future.isoformat(), "capacity": 1},
        )
        assert r.status_code == 201
        slot_id = r.json()["id"]

        client.post("/api/auth/logout")
        client.post(
            "/api/auth/candidate/login",
            json={"candidate_id": candidate_id, "password": "pw-content1"},
        )
        client.post(f"/api/slots/{slot_id}/book")

        file_key = MANIFEST[0]["file_key"]
        r = client.get(f"/api/content/{file_key}")
        assert r.status_code == 403


class TestContentListUnlocked:
    """Unlocked candidate → GET /api/content lists manifest entries whose files exist."""

    def test_unlocked_list_returns_200_with_manifest_entries(
        self, client, db_session, patch_content_dir
    ):
        """Unlocked candidate sees all manifest entries (files exist in tmp dir)."""
        candidate_id = create_and_activate_candidate(client, db_session)
        make_candidate_unlocked(client, db_session, candidate_id)

        r = client.get("/api/content")
        assert r.status_code == 200
        entries = r.json()
        assert isinstance(entries, list)
        # All MANIFEST entries should appear (all placeholder files exist)
        assert len(entries) == len(MANIFEST)
        # Check shape
        for entry in entries:
            assert "file_key" in entry
            assert "label" in entry
            assert "category" in entry
            # media_type and filename must NOT be leaked
            assert "media_type" not in entry

    def test_unlocked_list_excludes_missing_files(self, client, db_session, tmp_path, monkeypatch):
        """Only entries whose file exists on disk are listed."""
        # Put only the first MANIFEST file in tmp_path
        first_entry = MANIFEST[0]
        (tmp_path / first_entry["filename"]).write_bytes(b"data")

        from app.config import get_settings
        settings = get_settings()
        monkeypatch.setattr(settings, "content_dir", str(tmp_path))

        candidate_id = create_and_activate_candidate(client, db_session)
        make_candidate_unlocked(client, db_session, candidate_id)

        r = client.get("/api/content")
        assert r.status_code == 200
        entries = r.json()
        keys = [e["file_key"] for e in entries]
        assert first_entry["file_key"] in keys
        # All other keys must NOT appear (files missing)
        for m in MANIFEST[1:]:
            assert m["file_key"] not in keys


class TestContentDownloadUnlocked:
    """Unlocked candidate downloads a known file → 200 with correct body + headers + audit."""

    def test_known_file_returns_200_with_correct_bytes(
        self, client, db_session, patch_content_dir, content_dir
    ):
        """Response body equals the placeholder file's bytes."""
        candidate_id = create_and_activate_candidate(client, db_session)
        make_candidate_unlocked(client, db_session, candidate_id)

        entry = MANIFEST[0]
        expected_bytes = (content_dir / entry["filename"]).read_bytes()

        r = client.get(f"/api/content/{entry['file_key']}")
        assert r.status_code == 200
        assert r.content == expected_bytes

    def test_known_file_content_disposition_has_manifest_filename(
        self, client, db_session, patch_content_dir
    ):
        """Content-Disposition header contains the manifest filename."""
        candidate_id = create_and_activate_candidate(client, db_session)
        make_candidate_unlocked(client, db_session, candidate_id)

        entry = MANIFEST[0]
        r = client.get(f"/api/content/{entry['file_key']}")
        assert r.status_code == 200
        disposition = r.headers.get("content-disposition", "")
        assert entry["filename"] in disposition

    def test_download_writes_download_event_row(
        self, client, db_session, patch_content_dir
    ):
        """A DownloadEvent row is written after a successful download."""
        candidate_id = create_and_activate_candidate(client, db_session)
        make_candidate_unlocked(client, db_session, candidate_id)

        entry = MANIFEST[0]
        r = client.get(f"/api/content/{entry['file_key']}")
        assert r.status_code == 200

        # Refresh session to see committed data
        db_session.expire_all()
        cand_row = db_session.execute(
            select(Candidate).where(Candidate.candidate_id == candidate_id)
        ).scalar_one()
        event = db_session.execute(
            select(DownloadEvent).where(
                DownloadEvent.candidate_id == cand_row.id,
                DownloadEvent.file_key == entry["file_key"],
            )
        ).scalar_one_or_none()
        assert event is not None, "DownloadEvent row must be written on success"

    def test_download_writes_audit_row(
        self, client, db_session, patch_content_dir
    ):
        """An AuditLog row with action='file_download' and detail=file_key is written."""
        candidate_id = create_and_activate_candidate(client, db_session)
        make_candidate_unlocked(client, db_session, candidate_id)

        entry = MANIFEST[0]
        r = client.get(f"/api/content/{entry['file_key']}")
        assert r.status_code == 200

        db_session.expire_all()
        audit = db_session.execute(
            select(AuditLog).where(
                AuditLog.action == "file_download",
                AuditLog.actor == candidate_id,
                AuditLog.detail == entry["file_key"],
            )
        ).scalar_one_or_none()
        assert audit is not None, "AuditLog row for file_download must be written"


class TestContentDownloadUnknownKey:
    """Unknown file_key → 404 and NO download_event or audit row written."""

    def test_unknown_key_returns_404(self, client, db_session, patch_content_dir):
        """GET /api/content/totally_unknown → 404."""
        candidate_id = create_and_activate_candidate(client, db_session)
        make_candidate_unlocked(client, db_session, candidate_id)

        r = client.get("/api/content/totally_unknown_key")
        assert r.status_code == 404

    def test_unknown_key_no_download_event_written(
        self, client, db_session, patch_content_dir
    ):
        """No DownloadEvent row for a 404 download attempt."""
        candidate_id = create_and_activate_candidate(client, db_session)
        make_candidate_unlocked(client, db_session, candidate_id)

        client.get("/api/content/totally_unknown_key")

        db_session.expire_all()
        events = db_session.execute(select(DownloadEvent)).scalars().all()
        assert len(events) == 0, "No DownloadEvent should be written for a 404"

    def test_unknown_key_no_audit_row_written(
        self, client, db_session, patch_content_dir
    ):
        """No AuditLog row for a 404 download attempt."""
        candidate_id = create_and_activate_candidate(client, db_session)
        make_candidate_unlocked(client, db_session, candidate_id)

        client.get("/api/content/totally_unknown_key")

        db_session.expire_all()
        audit = db_session.execute(
            select(AuditLog).where(AuditLog.action == "file_download")
        ).scalar_one_or_none()
        assert audit is None, "No AuditLog row should be written for a 404"
