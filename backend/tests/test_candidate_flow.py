from app.seed import seed_admin_and_config


def login_admin(client):
    client.post("/api/auth/admin/login", json={"username": "admin", "password": "changeme"})


def test_full_candidate_lifecycle(client, db_session):
    seed_admin_and_config(db_session)
    login_admin(client)

    created = client.post("/api/admin/candidates", json={"first_name": "Ada"})
    assert created.status_code == 201
    data = created.json()
    candidate_id = data["candidate_id"]
    # IDs are random 4-digit (cand-XXXX) so the candidate count is not revealed.
    assert candidate_id.startswith("cand-")
    assert candidate_id[len("cand-"):].isdigit()
    assert data["status"] == "invited"
    token = data["set_password_path"].split("token=")[1]

    # candidate sets password (no auth required, just token)
    sp = client.post(
        "/api/auth/candidate/set-password",
        json={"token": token, "password": "pw-123456"},
    )
    assert sp.status_code == 200

    # candidate logs in
    client.post("/api/auth/logout")
    li = client.post(
        "/api/auth/candidate/login",
        json={"candidate_id": candidate_id, "password": "pw-123456"},
    )
    assert li.status_code == 200
    me = client.get("/api/auth/me")
    assert me.json()["role"] == "candidate"


def test_set_password_bad_token(client, db_session):
    seed_admin_and_config(db_session)
    r = client.post(
        "/api/auth/candidate/set-password",
        json={"token": "nope", "password": "pw-123456"},
    )
    assert r.status_code == 400


def test_create_candidate_requires_admin(client, db_session):
    seed_admin_and_config(db_session)
    r = client.post("/api/admin/candidates", json={"first_name": "Ada"})
    assert r.status_code == 401


def test_set_password_token_is_single_use(client, db_session):
    seed_admin_and_config(db_session)
    login_admin(client)
    data = client.post("/api/admin/candidates", json={"first_name": "Ada"}).json()
    token = data["set_password_path"].split("token=")[1]

    # First use — must succeed
    r1 = client.post(
        "/api/auth/candidate/set-password",
        json={"token": token, "password": "pw-first123"},
    )
    assert r1.status_code == 200

    # Second use with same token — must be rejected (token is single-use)
    r2 = client.post(
        "/api/auth/candidate/set-password",
        json={"token": token, "password": "pw-second456"},
    )
    assert r2.status_code == 400


def test_no_password_in_audit(client, db_session):
    from app.models import AuditLog
    seed_admin_and_config(db_session)
    login_admin(client)
    data = client.post("/api/admin/candidates", json={"first_name": "Ada"}).json()
    token = data["set_password_path"].split("token=")[1]
    client.post(
        "/api/auth/candidate/set-password",
        json={"token": token, "password": "supersecretpw"},
    )
    details = " ".join(r.detail or "" for r in db_session.query(AuditLog).all())
    assert "supersecretpw" not in details
    assert token not in details
