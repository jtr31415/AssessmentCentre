"""In-app notification counts: admin (unanswered questions) + candidate (unseen answers)."""

from sqlalchemy import select

from app.models import Question
from app.seed import seed_admin_and_config


def login_admin(client):
    client.post("/api/auth/admin/login", json={"username": "admin", "password": "changeme"})


def create_candidate_with_nda(client, db_session):
    seed_admin_and_config(db_session)
    login_admin(client)
    data = client.post("/api/admin/candidates", json={"first_name": "Nora"}).json()
    token = data["set_password_path"].split("token=")[1]
    client.post("/api/auth/candidate/set-password", json={"token": token, "password": "pw-notif12"})
    client.post("/api/auth/logout")
    client.post(
        "/api/auth/candidate/login",
        json={"candidate_id": data["candidate_id"], "password": "pw-notif12"},
    )
    client.post("/api/me/nda/accept")
    return data["candidate_id"]


def _relogin_candidate(client, candidate_id):
    client.post("/api/auth/logout")
    client.post(
        "/api/auth/candidate/login",
        json={"candidate_id": candidate_id, "password": "pw-notif12"},
    )


def test_full_notification_cycle(client, db_session):
    candidate_id = create_candidate_with_nda(client, db_session)

    # Candidate asks a question
    r = client.post("/api/me/questions", json={"body": "Which dataset is canonical?"})
    assert r.status_code == 201
    qid = r.json()["id"]

    # Candidate has no unseen answers yet
    assert client.get("/api/me/notifications").json()["answered_unseen"] == 0

    # Admin sees one unanswered question
    client.post("/api/auth/logout")
    login_admin(client)
    assert client.get("/api/admin/notifications").json()["unanswered_questions"] == 1

    # Admin answers it
    client.post(f"/api/admin/questions/{qid}/answer", json={"answer": "Use turbine_data.csv."})
    assert client.get("/api/admin/notifications").json()["unanswered_questions"] == 0

    # Candidate now has one unseen answer
    _relogin_candidate(client, candidate_id)
    assert client.get("/api/me/notifications").json()["answered_unseen"] == 1

    # Viewing the thread marks it seen → notification clears
    client.get("/api/me/questions")
    assert client.get("/api/me/notifications").json()["answered_unseen"] == 0

    db_session.expire_all()
    q = db_session.execute(select(Question).where(Question.id == qid)).scalar_one()
    assert q.answer_seen_at is not None


def test_admin_notifications_requires_admin(client, db_session):
    seed_admin_and_config(db_session)
    assert client.get("/api/admin/notifications").status_code == 401


def test_candidate_notifications_requires_candidate(client, db_session):
    seed_admin_and_config(db_session)
    assert client.get("/api/me/notifications").status_code == 401
