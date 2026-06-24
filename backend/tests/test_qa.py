"""Tests for private candidate Q&A + admin question queue (Phase 4, Task 1).

Fixtures: shared db_session + client from conftest (DO NOT define a local engine).
Pattern mirrors test_candidate_flow.py for seeding and candidate login.
"""

from app.models import AuditLog
from app.seed import seed_admin_and_config  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers (mirror test_candidate_flow.py pattern)
# ---------------------------------------------------------------------------

def login_admin(client):
    client.post("/api/auth/admin/login", json={"username": "admin", "password": "changeme"})


def create_and_login_candidate(client, db_session, first_name: str) -> dict:
    """Create a candidate via admin, set password, login; returns login response data."""
    login_admin(client)
    created = client.post("/api/admin/candidates", json={"first_name": first_name})
    assert created.status_code == 201, created.text
    data = created.json()
    token = data["set_password_path"].split("token=")[1]
    candidate_id = data["candidate_id"]

    client.post("/api/auth/logout")
    sp = client.post(
        "/api/auth/candidate/set-password",
        json={"token": token, "password": "pw-123456"},
    )
    assert sp.status_code == 200, sp.text

    li = client.post(
        "/api/auth/candidate/login",
        json={"candidate_id": candidate_id, "password": "pw-123456"},
    )
    assert li.status_code == 200, li.text
    return {"candidate_id": candidate_id}


# ---------------------------------------------------------------------------
# Test: candidate submits a question → 201; appears in their list; answer null
# ---------------------------------------------------------------------------

def test_candidate_submit_question(client, db_session):
    seed_admin_and_config(db_session)
    create_and_login_candidate(client, db_session, "Ada")

    r = client.post("/api/me/questions", json={"body": "When does the assessment start?"})
    assert r.status_code == 201, r.text
    data = r.json()
    assert "id" in data
    assert data["body"] == "When does the assessment start?"
    assert data["answer"] is None
    assert data["answered_at"] is None
    assert "asked_at" in data


def test_candidate_list_own_questions_includes_sla(client, db_session):
    seed_admin_and_config(db_session)
    create_and_login_candidate(client, db_session, "Ada")

    client.post("/api/me/questions", json={"body": "How long is the test?"})

    r = client.get("/api/me/questions")
    assert r.status_code == 200, r.text
    data = r.json()
    assert "questions" in data
    assert "sla_text" in data
    assert len(data["questions"]) == 1
    assert data["questions"][0]["answer"] is None
    assert data["sla_text"]  # non-empty string


# ---------------------------------------------------------------------------
# Test: PRIVACY — candidate B cannot see candidate A's questions
# ---------------------------------------------------------------------------

def test_privacy_candidate_b_cannot_see_a_questions(client, db_session):
    seed_admin_and_config(db_session)

    # Create candidate A and submit a question
    create_and_login_candidate(client, db_session, "Ada")
    r = client.post("/api/me/questions", json={"body": "A's secret question"})
    assert r.status_code == 201, r.text
    a_question_id = r.json()["id"]

    # Logout A, create and login candidate B
    client.post("/api/auth/logout")
    login_admin(client)
    b_data = client.post("/api/admin/candidates", json={"first_name": "Bob"}).json()
    b_token = b_data["set_password_path"].split("token=")[1]
    b_candidate_id = b_data["candidate_id"]

    client.post("/api/auth/logout")
    client.post(
        "/api/auth/candidate/set-password",
        json={"token": b_token, "password": "pw-123456"},
    )
    client.post(
        "/api/auth/candidate/login",
        json={"candidate_id": b_candidate_id, "password": "pw-123456"},
    )

    # B's question list must NOT contain A's question
    r_b = client.get("/api/me/questions")
    assert r_b.status_code == 200, r_b.text
    b_questions = r_b.json()["questions"]
    b_ids = [q["id"] for q in b_questions]
    assert a_question_id not in b_ids


# ---------------------------------------------------------------------------
# Test: admin sees ALL questions with asker info and correct candidate_id
# ---------------------------------------------------------------------------

def test_admin_sees_all_questions(client, db_session):
    seed_admin_and_config(db_session)

    a_info = create_and_login_candidate(client, db_session, "Ada")
    r_a = client.post("/api/me/questions", json={"body": "A asks about schedule"})
    assert r_a.status_code == 201
    a_cid = a_info["candidate_id"]

    client.post("/api/auth/logout")
    login_admin(client)
    b_data = client.post("/api/admin/candidates", json={"first_name": "Bob"}).json()
    b_token = b_data["set_password_path"].split("token=")[1]
    b_cid = b_data["candidate_id"]
    client.post("/api/auth/logout")
    client.post(
        "/api/auth/candidate/set-password",
        json={"token": b_token, "password": "pw-123456"},
    )
    client.post(
        "/api/auth/candidate/login",
        json={"candidate_id": b_cid, "password": "pw-123456"},
    )
    r_b = client.post("/api/me/questions", json={"body": "B asks about tools"})
    assert r_b.status_code == 201

    # Login as admin and check queue
    client.post("/api/auth/logout")
    login_admin(client)
    r = client.get("/api/admin/questions")
    assert r.status_code == 200, r.text
    questions = r.json()
    cids = {q["candidate_id"] for q in questions}
    assert a_cid in cids
    assert b_cid in cids
    # each question has required fields
    for q in questions:
        assert "id" in q
        assert "first_name" in q
        assert "body" in q
        assert "asked_at" in q
        assert "answer" in q
        assert "answered_at" in q
        assert "answered" in q


# ---------------------------------------------------------------------------
# Test: admin answers a question → candidate sees answer; admin queue flags it
# ---------------------------------------------------------------------------

def test_admin_answer_visible_to_candidate(client, db_session):
    seed_admin_and_config(db_session)

    a_info = create_and_login_candidate(client, db_session, "Ada")
    r = client.post("/api/me/questions", json={"body": "What time zone?"})
    assert r.status_code == 201
    question_id = r.json()["id"]

    # Admin answers
    client.post("/api/auth/logout")
    login_admin(client)
    ans = client.post(
        f"/api/admin/questions/{question_id}/answer",
        json={"answer": "UTC"},
    )
    assert ans.status_code == 200, ans.text

    # Candidate sees answer
    client.post("/api/auth/logout")
    client.post(
        "/api/auth/candidate/login",
        json={"candidate_id": a_info["candidate_id"], "password": "pw-123456"},
    )
    r2 = client.get("/api/me/questions")
    assert r2.status_code == 200
    questions = r2.json()["questions"]
    assert len(questions) == 1
    assert questions[0]["answer"] == "UTC"
    assert questions[0]["answered_at"] is not None

    # Admin queue reflects answered flag
    client.post("/api/auth/logout")
    login_admin(client)
    r3 = client.get("/api/admin/questions")
    answered = [q for q in r3.json() if q["id"] == question_id]
    assert len(answered) == 1
    assert answered[0]["answered"] is True


# ---------------------------------------------------------------------------
# Test: empty / whitespace body → rejected (422 or 400)
# ---------------------------------------------------------------------------

def test_empty_body_rejected(client, db_session):
    seed_admin_and_config(db_session)
    create_and_login_candidate(client, db_session, "Ada")

    r = client.post("/api/me/questions", json={"body": ""})
    assert r.status_code in (400, 422), r.text


def test_whitespace_body_rejected(client, db_session):
    seed_admin_and_config(db_session)
    create_and_login_candidate(client, db_session, "Ada")

    r = client.post("/api/me/questions", json={"body": "   "})
    assert r.status_code in (400, 422), r.text


# ---------------------------------------------------------------------------
# Test: candidate cannot hit admin endpoints → 401
# ---------------------------------------------------------------------------

def test_candidate_cannot_access_admin_questions(client, db_session):
    seed_admin_and_config(db_session)
    create_and_login_candidate(client, db_session, "Ada")

    r = client.get("/api/admin/questions")
    assert r.status_code == 401, r.text


def test_candidate_cannot_answer_questions(client, db_session):
    seed_admin_and_config(db_session)
    create_and_login_candidate(client, db_session, "Ada")
    r_q = client.post("/api/me/questions", json={"body": "Can I answer my own?"})
    assert r_q.status_code == 201
    qid = r_q.json()["id"]

    r = client.post(f"/api/admin/questions/{qid}/answer", json={"answer": "nope"})
    assert r.status_code == 401, r.text


# ---------------------------------------------------------------------------
# Test: admin answer endpoint → 404 for missing question
# ---------------------------------------------------------------------------

def test_admin_answer_missing_question_404(client, db_session):
    seed_admin_and_config(db_session)
    login_admin(client)

    r = client.post("/api/admin/questions/99999/answer", json={"answer": "hi"})
    assert r.status_code == 404, r.text


# ---------------------------------------------------------------------------
# Test: empty / whitespace answer → rejected (422); question stays unanswered
# ---------------------------------------------------------------------------

def test_admin_empty_answer_rejected(client, db_session):
    seed_admin_and_config(db_session)
    create_and_login_candidate(client, db_session, "Ada")

    r_q = client.post("/api/me/questions", json={"body": "Any answer?"})
    assert r_q.status_code == 201
    question_id = r_q.json()["id"]

    client.post("/api/auth/logout")
    login_admin(client)

    # Empty string → 422
    r1 = client.post(f"/api/admin/questions/{question_id}/answer", json={"answer": ""})
    assert r1.status_code == 422, r1.text

    # Whitespace-only → 422
    r2 = client.post(f"/api/admin/questions/{question_id}/answer", json={"answer": "   "})
    assert r2.status_code == 422, r2.text

    # Question must remain unanswered
    r3 = client.get("/api/admin/questions")
    assert r3.status_code == 200
    matching = [q for q in r3.json() if q["id"] == question_id]
    assert len(matching) == 1
    assert matching[0]["answered"] is False
    assert matching[0]["answer"] is None


# ---------------------------------------------------------------------------
# Test: audit detail NEVER contains question body or answer text
# ---------------------------------------------------------------------------

def test_no_question_body_or_answer_in_audit(client, db_session):
    seed_admin_and_config(db_session)
    create_and_login_candidate(client, db_session, "Ada")

    body_text = "What is the meaning of life exactly?"
    r_q = client.post("/api/me/questions", json={"body": body_text})
    assert r_q.status_code == 201
    question_id = r_q.json()["id"]

    answer_text = "Forty-two and some extra chars"
    client.post("/api/auth/logout")
    login_admin(client)
    client.post(
        f"/api/admin/questions/{question_id}/answer",
        json={"answer": answer_text},
    )

    all_details = " ".join(row.detail or "" for row in db_session.query(AuditLog).all())
    assert body_text not in all_details, "question body leaked into audit detail"
    assert answer_text not in all_details, "answer text leaked into audit detail"


# ---------------------------------------------------------------------------
# Test: unanswered questions appear before answered in admin queue
# ---------------------------------------------------------------------------

def test_admin_queue_unanswered_first(client, db_session):
    seed_admin_and_config(db_session)
    create_and_login_candidate(client, db_session, "Ada")

    r1 = client.post("/api/me/questions", json={"body": "Question one"})
    r2 = client.post("/api/me/questions", json={"body": "Question two"})
    assert r1.status_code == 201
    assert r2.status_code == 201
    q1_id = r1.json()["id"]

    # Admin answers question 1
    client.post("/api/auth/logout")
    login_admin(client)
    client.post(f"/api/admin/questions/{q1_id}/answer", json={"answer": "answered"})

    r = client.get("/api/admin/questions")
    questions = r.json()
    # First item should be unanswered
    assert questions[0]["answered"] is False
