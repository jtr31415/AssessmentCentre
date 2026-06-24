"""
Tests for admin account management endpoints:
  POST /api/admin/candidates/{candidate_id}/reset-password
  POST /api/admin/candidates/{candidate_id}/reissue-invite
  POST /api/admin/candidates/{candidate_id}/disable
  POST /api/admin/candidates/{candidate_id}/enable
"""
from app.models import AuditLog
from app.seed import seed_admin_and_config

# ---------------------------------------------------------------------------
# Helpers (mirroring test_candidate_flow.py style)
# ---------------------------------------------------------------------------

def login_admin(client):
    client.post("/api/auth/admin/login", json={"username": "admin", "password": "changeme"})


def create_candidate(client, first_name="Ada"):
    return client.post("/api/admin/candidates", json={"first_name": first_name}).json()


def set_password(client, token, password="pw-Testing1"):
    return client.post(
        "/api/auth/candidate/set-password",
        json={"token": token, "password": password},
    )


def login_candidate(client, candidate_id, password="pw-Testing1"):
    client.post("/api/auth/logout")
    return client.post(
        "/api/auth/candidate/login",
        json={"candidate_id": candidate_id, "password": password},
    )


def extract_token(set_password_path: str) -> str:
    return set_password_path.split("token=")[1]


# ---------------------------------------------------------------------------
# reset-password
# ---------------------------------------------------------------------------

def test_reset_password_returns_set_password_path(client, db_session):
    seed_admin_and_config(db_session)
    login_admin(client)

    data = create_candidate(client)
    cid = data["candidate_id"]
    original_token = extract_token(data["set_password_path"])

    r = client.post(f"/api/admin/candidates/{cid}/reset-password")
    assert r.status_code == 200
    body = r.json()
    assert "set_password_path" in body
    new_token = extract_token(body["set_password_path"])
    # Token must differ from the original
    assert new_token != original_token


def test_reset_password_new_token_is_usable(client, db_session):
    """Using the new token via set-password works; candidate can then log in."""
    seed_admin_and_config(db_session)
    login_admin(client)

    data = create_candidate(client)
    cid = data["candidate_id"]

    # Reset password
    r = client.post(f"/api/admin/candidates/{cid}/reset-password")
    new_token = extract_token(r.json()["set_password_path"])

    # Use new token to set a password
    sp = set_password(client, new_token, "NewPass-999")
    assert sp.status_code == 200

    # Candidate can log in with new password
    li = login_candidate(client, cid, "NewPass-999")
    assert li.status_code == 200


def test_reset_password_token_not_in_audit(client, db_session):
    seed_admin_and_config(db_session)
    login_admin(client)

    data = create_candidate(client)
    cid = data["candidate_id"]
    r = client.post(f"/api/admin/candidates/{cid}/reset-password")
    new_token = extract_token(r.json()["set_password_path"])

    details = " ".join(row.detail or "" for row in db_session.query(AuditLog).all())
    assert new_token not in details


def test_reset_password_requires_admin(client, db_session):
    seed_admin_and_config(db_session)
    login_admin(client)
    data = create_candidate(client)
    cid = data["candidate_id"]

    client.post("/api/auth/logout")
    r = client.post(f"/api/admin/candidates/{cid}/reset-password")
    assert r.status_code == 401


def test_reset_password_404_for_unknown(client, db_session):
    seed_admin_and_config(db_session)
    login_admin(client)
    r = client.post("/api/admin/candidates/no-such-id/reset-password")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# reissue-invite
# ---------------------------------------------------------------------------

def test_reissue_invite_gives_fresh_token(client, db_session):
    seed_admin_and_config(db_session)
    login_admin(client)

    data = create_candidate(client)
    cid = data["candidate_id"]
    original_token = extract_token(data["set_password_path"])

    r = client.post(f"/api/admin/candidates/{cid}/reissue-invite")
    assert r.status_code == 200
    new_token = extract_token(r.json()["set_password_path"])
    assert new_token != original_token


def test_reissue_invite_new_token_works(client, db_session):
    seed_admin_and_config(db_session)
    login_admin(client)

    data = create_candidate(client)
    cid = data["candidate_id"]

    r = client.post(f"/api/admin/candidates/{cid}/reissue-invite")
    new_token = extract_token(r.json()["set_password_path"])

    sp = set_password(client, new_token, "Invite-Pass1")
    assert sp.status_code == 200

    li = login_candidate(client, cid, "Invite-Pass1")
    assert li.status_code == 200


def test_reissue_invite_token_not_in_audit(client, db_session):
    seed_admin_and_config(db_session)
    login_admin(client)

    data = create_candidate(client)
    cid = data["candidate_id"]
    r = client.post(f"/api/admin/candidates/{cid}/reissue-invite")
    new_token = extract_token(r.json()["set_password_path"])

    details = " ".join(row.detail or "" for row in db_session.query(AuditLog).all())
    assert new_token not in details


def test_reissue_invite_requires_admin(client, db_session):
    seed_admin_and_config(db_session)
    login_admin(client)
    data = create_candidate(client)
    cid = data["candidate_id"]

    client.post("/api/auth/logout")
    r = client.post(f"/api/admin/candidates/{cid}/reissue-invite")
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# disable
# ---------------------------------------------------------------------------

def test_disable_returns_disabled_status(client, db_session):
    seed_admin_and_config(db_session)
    login_admin(client)

    data = create_candidate(client)
    cid = data["candidate_id"]

    r = client.post(f"/api/admin/candidates/{cid}/disable")
    assert r.status_code == 200
    assert r.json()["status"] == "disabled"


def test_disable_prevents_login(client, db_session):
    """After disable, candidate login returns 401 even with correct password."""
    seed_admin_and_config(db_session)
    login_admin(client)

    data = create_candidate(client)
    cid = data["candidate_id"]
    token = extract_token(data["set_password_path"])

    # Candidate sets password first
    set_password(client, token, "pw-Testing1")

    # Admin disables candidate
    client.post(f"/api/admin/candidates/{cid}/disable")

    # Login attempt must fail
    li = login_candidate(client, cid, "pw-Testing1")
    assert li.status_code == 401


def test_disable_requires_admin(client, db_session):
    seed_admin_and_config(db_session)
    login_admin(client)
    data = create_candidate(client)
    cid = data["candidate_id"]

    client.post("/api/auth/logout")
    r = client.post(f"/api/admin/candidates/{cid}/disable")
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# enable
# ---------------------------------------------------------------------------

def test_enable_with_password_restores_active_and_login(client, db_session):
    seed_admin_and_config(db_session)
    login_admin(client)

    data = create_candidate(client)
    cid = data["candidate_id"]
    token = extract_token(data["set_password_path"])
    set_password(client, token, "pw-Testing1")

    # Disable then enable
    client.post(f"/api/admin/candidates/{cid}/disable")
    r = client.post(f"/api/admin/candidates/{cid}/enable")
    assert r.status_code == 200
    assert r.json()["status"] == "active"

    li = login_candidate(client, cid, "pw-Testing1")
    assert li.status_code == 200


def test_enable_without_password_yields_invited(client, db_session):
    """Enable a candidate who never set a password → status 'invited'."""
    seed_admin_and_config(db_session)
    login_admin(client)

    data = create_candidate(client)
    cid = data["candidate_id"]

    # Disable without ever setting password
    client.post(f"/api/admin/candidates/{cid}/disable")

    r = client.post(f"/api/admin/candidates/{cid}/enable")
    assert r.status_code == 200
    assert r.json()["status"] == "invited"


def test_enable_requires_admin(client, db_session):
    seed_admin_and_config(db_session)
    login_admin(client)
    data = create_candidate(client)
    cid = data["candidate_id"]

    client.post("/api/auth/logout")
    r = client.post(f"/api/admin/candidates/{cid}/enable")
    assert r.status_code == 401
