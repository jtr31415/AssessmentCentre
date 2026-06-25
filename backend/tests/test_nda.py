"""NDA acceptance gating at first login.

A logged-in candidate who has NOT accepted the NDA cannot take part (book,
submit questions, access content/data). Accepting unlocks participation;
declining blocks it; accepting after a decline clears the decline.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.models import Candidate
from app.seed import seed_admin_and_config


def login_admin(client):
    client.post("/api/auth/admin/login", json={"username": "admin", "password": "changeme"})


def create_and_login_candidate_no_nda(client, db_session):
    """Create + activate + login a candidate WITHOUT accepting the NDA. Returns candidate_id."""
    seed_admin_and_config(db_session)
    login_admin(client)
    data = client.post("/api/admin/candidates", json={"first_name": "Ndatester"}).json()
    token = data["set_password_path"].split("token=")[1]
    client.post("/api/auth/candidate/set-password", json={"token": token, "password": "pw-nda1234"})
    client.post("/api/auth/logout")
    li = client.post(
        "/api/auth/candidate/login",
        json={"candidate_id": data["candidate_id"], "password": "pw-nda1234"},
    )
    assert li.status_code == 200
    return data["candidate_id"]


def _make_slot(client):
    client.post("/api/auth/logout")
    login_admin(client)
    future = datetime.now(UTC) + timedelta(days=20)
    r = client.post("/api/admin/slots", json={"starts_at": future.isoformat(), "capacity": 1})
    assert r.status_code == 201
    return r.json()["id"]


def _relogin(client, candidate_id):
    client.post("/api/auth/logout")
    client.post(
        "/api/auth/candidate/login",
        json={"candidate_id": candidate_id, "password": "pw-nda1234"},
    )


class TestProfileNdaState:
    def test_profile_reports_undecided(self, client, db_session):
        create_and_login_candidate_no_nda(client, db_session)
        p = client.get("/api/me/profile").json()
        assert p["nda_accepted"] is False
        assert p["nda_declined"] is False


class TestGatingWithoutAcceptance:
    def test_booking_blocked_without_nda(self, client, db_session):
        cid = create_and_login_candidate_no_nda(client, db_session)
        slot_id = _make_slot(client)
        _relogin(client, cid)
        r = client.post(f"/api/slots/{slot_id}/book")
        assert r.status_code == 403
        assert "NDA" in r.json()["detail"]

    def test_question_blocked_without_nda(self, client, db_session):
        create_and_login_candidate_no_nda(client, db_session)
        r = client.post("/api/me/questions", json={"body": "hi"})
        assert r.status_code == 403
        assert "NDA" in r.json()["detail"]

    def test_content_blocked_without_nda(self, client, db_session):
        create_and_login_candidate_no_nda(client, db_session)
        r = client.get("/api/content")
        assert r.status_code == 403
        assert "NDA" in r.json()["detail"]


class TestAcceptDecline:
    def test_accept_unlocks_participation(self, client, db_session):
        cid = create_and_login_candidate_no_nda(client, db_session)
        acc = client.post("/api/me/nda/accept")
        assert acc.status_code == 200
        assert acc.json()["nda_accepted"] is True

        p = client.get("/api/me/profile").json()
        assert p["nda_accepted"] is True
        assert p["nda_declined"] is False

        slot_id = _make_slot(client)
        _relogin(client, cid)
        assert client.post(f"/api/slots/{slot_id}/book").status_code == 201

    def test_decline_blocks_participation(self, client, db_session):
        cid = create_and_login_candidate_no_nda(client, db_session)
        dec = client.post("/api/me/nda/decline")
        assert dec.status_code == 200
        assert dec.json()["nda_declined"] is True

        p = client.get("/api/me/profile").json()
        assert p["nda_accepted"] is False
        assert p["nda_declined"] is True

        slot_id = _make_slot(client)
        _relogin(client, cid)
        assert client.post(f"/api/slots/{slot_id}/book").status_code == 403

    def test_accept_after_decline_clears_decline(self, client, db_session):
        cid = create_and_login_candidate_no_nda(client, db_session)
        client.post("/api/me/nda/decline")
        client.post("/api/me/nda/accept")

        db_session.expire_all()
        cand = db_session.execute(
            select(Candidate).where(Candidate.candidate_id == cid)
        ).scalar_one()
        assert cand.nda_accepted_at is not None
        assert cand.nda_declined_at is None

        p = client.get("/api/me/profile").json()
        assert p["nda_accepted"] is True
        assert p["nda_declined"] is False
