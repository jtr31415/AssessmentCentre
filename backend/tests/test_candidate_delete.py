"""Individual candidate deletion (confirmed by typing the candidate ID)."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.models import AuditLog, Booking, Candidate, DownloadEvent, Question, Slot
from app.seed import seed_admin_and_config


def login_admin(client):
    client.post("/api/auth/admin/login", json={"username": "admin", "password": "changeme"})


def test_delete_candidate_cascades(client, db_session):
    seed_admin_and_config(db_session)
    login_admin(client)
    cid = client.post("/api/admin/candidates", json={"first_name": "Doomed"}).json()["candidate_id"]

    cand = db_session.execute(
        select(Candidate).where(Candidate.candidate_id == cid)
    ).scalar_one()
    slot = Slot(starts_at=datetime.now(UTC) + timedelta(days=5))
    db_session.add(slot)
    db_session.flush()
    db_session.add(Booking(candidate_id=cand.id, slot_id=slot.id, unlock_at=datetime.now(UTC)))
    db_session.add(Question(candidate_id=cand.id, body="a question"))
    db_session.add(DownloadEvent(candidate_id=cand.id, file_key="k"))
    db_session.add(AuditLog(actor=cid, action="login"))
    db_session.commit()

    # Wrong confirmation → 400, candidate untouched
    r = client.request("DELETE", f"/api/admin/candidates/{cid}", json={"confirm": "nope"})
    assert r.status_code == 400
    still = db_session.execute(
        select(Candidate).where(Candidate.candidate_id == cid)
    ).scalar_one_or_none()
    assert still is not None

    # Correct confirmation → deletes candidate + all their data
    r = client.request("DELETE", f"/api/admin/candidates/{cid}", json={"confirm": cid})
    assert r.status_code == 200, r.text

    db_session.expire_all()
    gone = db_session.execute(
        select(Candidate).where(Candidate.candidate_id == cid)
    ).scalar_one_or_none()
    assert gone is None
    assert db_session.execute(
        select(Booking).where(Booking.candidate_id == cand.id)
    ).scalar_one_or_none() is None
    assert db_session.execute(
        select(Question).where(Question.candidate_id == cand.id)
    ).scalar_one_or_none() is None
    assert db_session.execute(
        select(DownloadEvent).where(DownloadEvent.candidate_id == cand.id)
    ).scalar_one_or_none() is None
    # Candidate's own audit rows gone; the admin delete audit row is kept
    assert db_session.execute(
        select(AuditLog).where(AuditLog.actor == cid)
    ).scalar_one_or_none() is None
    assert db_session.execute(
        select(AuditLog).where(AuditLog.action == "candidate_delete")
    ).scalar_one_or_none() is not None


def test_delete_unknown_candidate_404(client, db_session):
    seed_admin_and_config(db_session)
    login_admin(client)
    r = client.request(
        "DELETE", "/api/admin/candidates/cand-9999", json={"confirm": "cand-9999"}
    )
    assert r.status_code == 404


def test_delete_requires_admin(client, db_session):
    seed_admin_and_config(db_session)
    r = client.request(
        "DELETE", "/api/admin/candidates/cand-1234", json={"confirm": "cand-1234"}
    )
    assert r.status_code == 401
