"""Tests for the DB-backed content library: admin upload/list/replace/delete and
candidate gated list/download.

Uses the shared ``db_session``/``client`` fixtures from conftest.py.  Do NOT
define a local ``engine`` fixture (it would drop the shared test schema).
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.models import AuditLog, Booking, Candidate, ContentFile, DownloadEvent
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
    client.post("/api/me/nda/accept")  # accept NDA at first login (gates participation)
    return data["candidate_id"]


def make_candidate_unlocked(client, db_session, candidate_id: str):
    """Give the candidate a booking whose unlock_at is in the past."""
    client.post("/api/auth/logout")
    login_admin(client)
    future = datetime.now(UTC) + timedelta(hours=1)
    r = client.post("/api/admin/slots", json={"starts_at": future.isoformat(), "capacity": 1})
    assert r.status_code == 201, r.text
    slot_id = r.json()["id"]

    client.post("/api/auth/logout")
    li = client.post(
        "/api/auth/candidate/login",
        json={"candidate_id": candidate_id, "password": "pw-content1"},
    )
    assert li.status_code == 200

    r = client.post(f"/api/slots/{slot_id}/book")
    assert r.status_code == 201, r.text

    cand_row = db_session.execute(
        select(Candidate).where(Candidate.candidate_id == candidate_id)
    ).scalar_one()
    booking = db_session.execute(
        select(Booking).where(Booking.candidate_id == cand_row.id)
    ).scalar_one()
    booking.unlock_at = datetime.now(UTC) - timedelta(hours=1)
    db_session.commit()


def admin_upload(client, label, category, filename, content, media_type="application/pdf"):
    """Upload a file as admin (caller must be logged in as admin). Returns the JSON body."""
    r = client.post(
        "/api/admin/content",
        files={"file": (filename, content, media_type)},
        data={"label": label, "category": category},
    )
    return r


@pytest.fixture()
def patch_content_dir(tmp_path, monkeypatch):
    """Point get_settings().content_dir at a fresh tmp dir for uploads + downloads."""
    from app.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "content_dir", str(tmp_path))
    return tmp_path


# ---------------------------------------------------------------------------
# Admin upload / validation
# ---------------------------------------------------------------------------


class TestAdminUpload:
    def test_upload_creates_row_and_file(self, client, db_session, patch_content_dir):
        seed_admin_and_config(db_session)
        login_admin(client)

        r = admin_upload(client, "Exercise Brief", "brief", "brief.pdf", b"%PDF-1.4 data")
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["label"] == "Exercise Brief"
        assert body["category"] == "brief"
        assert body["original_filename"] == "brief.pdf"
        assert body["size_bytes"] == len(b"%PDF-1.4 data")
        assert "file_key" in body

        # Row exists and the stored file is on disk.
        row = db_session.execute(
            select(ContentFile).where(ContentFile.file_key == body["file_key"])
        ).scalar_one()
        assert (patch_content_dir / row.stored_filename).read_bytes() == b"%PDF-1.4 data"

    def test_upload_requires_admin(self, client, db_session, patch_content_dir):
        seed_admin_and_config(db_session)
        r = admin_upload(client, "x", "brief", "x.pdf", b"data")
        assert r.status_code == 401

    def test_upload_rejects_bad_category(self, client, db_session, patch_content_dir):
        seed_admin_and_config(db_session)
        login_admin(client)
        r = admin_upload(client, "x", "nonsense", "x.pdf", b"data")
        assert r.status_code == 422

    def test_upload_rejects_empty_label(self, client, db_session, patch_content_dir):
        seed_admin_and_config(db_session)
        login_admin(client)
        r = admin_upload(client, "   ", "brief", "x.pdf", b"data")
        assert r.status_code == 422

    def test_upload_rejects_empty_file(self, client, db_session, patch_content_dir):
        seed_admin_and_config(db_session)
        login_admin(client)
        r = admin_upload(client, "x", "brief", "x.pdf", b"")
        assert r.status_code == 422

    def test_list_returns_uploaded(self, client, db_session, patch_content_dir):
        seed_admin_and_config(db_session)
        login_admin(client)
        admin_upload(client, "Brief", "brief", "a.pdf", b"a")
        admin_upload(client, "Data", "data", "b.csv", b"b", media_type="text/csv")

        r = client.get("/api/admin/content")
        assert r.status_code == 200
        rows = r.json()
        assert len(rows) == 2
        labels = {row["label"] for row in rows}
        assert labels == {"Brief", "Data"}

    def test_description_round_trips_to_candidate(self, client, db_session, patch_content_dir):
        seed_admin_and_config(db_session)
        login_admin(client)
        r = client.post(
            "/api/admin/content",
            files={"file": ("brief.pdf", b"PDFDATA", "application/pdf")},
            data={"label": "Brief", "category": "brief", "description": "Read this first."},
        )
        assert r.status_code == 201
        assert r.json()["description"] == "Read this first."
        # Admin list carries it
        assert client.get("/api/admin/content").json()[0]["description"] == "Read this first."

    def test_replace_can_update_description_only(self, client, db_session, patch_content_dir):
        seed_admin_and_config(db_session)
        login_admin(client)
        key = client.post(
            "/api/admin/content",
            files={"file": ("a.pdf", b"x", "application/pdf")},
            data={"label": "Brief", "category": "brief"},
        ).json()["file_key"]
        # Update description with no new file
        r = client.put(f"/api/admin/content/{key}", data={"description": "Now described."})
        assert r.status_code == 200
        assert r.json()["description"] == "Now described."
        # Clearing (whitespace-only strips to empty → None)
        r2 = client.put(f"/api/admin/content/{key}", data={"description": "   "})
        assert r2.json()["description"] is None

    def test_delete_removes_row_and_file(self, client, db_session, patch_content_dir):
        seed_admin_and_config(db_session)
        login_admin(client)
        body = admin_upload(client, "Brief", "brief", "a.pdf", b"a").json()
        file_key = body["file_key"]
        stored = db_session.execute(
            select(ContentFile).where(ContentFile.file_key == file_key)
        ).scalar_one().stored_filename
        assert (patch_content_dir / stored).exists()

        r = client.delete(f"/api/admin/content/{file_key}")
        assert r.status_code == 200

        db_session.expire_all()
        gone = db_session.execute(
            select(ContentFile).where(ContentFile.file_key == file_key)
        ).scalar_one_or_none()
        assert gone is None
        assert not (patch_content_dir / stored).exists()

    def test_replace_swaps_file_and_updates_label(self, client, db_session, patch_content_dir):
        seed_admin_and_config(db_session)
        login_admin(client)
        body = admin_upload(client, "Old", "brief", "a.pdf", b"old-bytes").json()
        file_key = body["file_key"]
        old_stored = db_session.execute(
            select(ContentFile).where(ContentFile.file_key == file_key)
        ).scalar_one().stored_filename

        r = client.put(
            f"/api/admin/content/{file_key}",
            files={"file": ("new.csv", b"new-bytes", "text/csv")},
            data={"label": "New", "category": "data"},
        )
        assert r.status_code == 200, r.text
        updated = r.json()
        assert updated["label"] == "New"
        assert updated["category"] == "data"
        assert updated["original_filename"] == "new.csv"

        db_session.expire_all()
        row = db_session.execute(
            select(ContentFile).where(ContentFile.file_key == file_key)
        ).scalar_one()
        # New file written, old removed.
        assert (patch_content_dir / row.stored_filename).read_bytes() == b"new-bytes"
        assert not (patch_content_dir / old_stored).exists()


# ---------------------------------------------------------------------------
# Candidate gated list/download
# ---------------------------------------------------------------------------


def _seed_one_file(client, db_session):
    """As admin, upload one file; return its file_key. Leaves session logged out."""
    login_admin(client)
    body = admin_upload(client, "Exercise Brief", "brief", "brief.pdf", b"PDFDATA").json()
    client.post("/api/auth/logout")
    return body["file_key"]


class TestCandidateGate:
    def test_locked_candidate_403_on_list(self, client, db_session, patch_content_dir):
        create_and_activate_candidate(client, db_session)  # no booking → locked
        r = client.get("/api/content")
        assert r.status_code == 403

    def test_locked_candidate_403_on_download(self, client, db_session, patch_content_dir):
        seed_admin_and_config(db_session)
        file_key = _seed_one_file(client, db_session)
        create_and_activate_candidate(client, db_session)
        r = client.get(f"/api/content/{file_key}")
        assert r.status_code == 403


class TestCandidateListDownload:
    def test_unlocked_list_shape(self, client, db_session, patch_content_dir):
        seed_admin_and_config(db_session)
        _seed_one_file(client, db_session)
        candidate_id = create_and_activate_candidate(client, db_session)
        make_candidate_unlocked(client, db_session, candidate_id)

        r = client.get("/api/content")
        assert r.status_code == 200
        entries = r.json()
        assert len(entries) == 1
        entry = entries[0]
        assert set(entry.keys()) == {"file_key", "label", "description", "category"}
        # internal fields must NOT leak
        assert "stored_filename" not in entry
        assert "media_type" not in entry

    def test_unlocked_download_returns_bytes_and_disposition(
        self, client, db_session, patch_content_dir
    ):
        seed_admin_and_config(db_session)
        file_key = _seed_one_file(client, db_session)
        candidate_id = create_and_activate_candidate(client, db_session)
        make_candidate_unlocked(client, db_session, candidate_id)

        r = client.get(f"/api/content/{file_key}")
        assert r.status_code == 200
        assert r.content == b"PDFDATA"
        assert "brief.pdf" in r.headers.get("content-disposition", "")

    def test_download_writes_event_and_audit(self, client, db_session, patch_content_dir):
        seed_admin_and_config(db_session)
        file_key = _seed_one_file(client, db_session)
        candidate_id = create_and_activate_candidate(client, db_session)
        make_candidate_unlocked(client, db_session, candidate_id)

        r = client.get(f"/api/content/{file_key}")
        assert r.status_code == 200

        db_session.expire_all()
        event = db_session.execute(
            select(DownloadEvent).where(DownloadEvent.file_key == file_key)
        ).scalar_one_or_none()
        assert event is not None
        audit = db_session.execute(
            select(AuditLog).where(
                AuditLog.action == "file_download",
                AuditLog.actor == candidate_id,
                AuditLog.detail == file_key,
            )
        ).scalar_one_or_none()
        assert audit is not None

    def test_unknown_key_404_no_event(self, client, db_session, patch_content_dir):
        seed_admin_and_config(db_session)
        candidate_id = create_and_activate_candidate(client, db_session)
        make_candidate_unlocked(client, db_session, candidate_id)

        r = client.get("/api/content/deadbeefdeadbeefdeadbeefdeadbeef")
        assert r.status_code == 404

        db_session.expire_all()
        assert db_session.execute(select(DownloadEvent)).scalars().all() == []
