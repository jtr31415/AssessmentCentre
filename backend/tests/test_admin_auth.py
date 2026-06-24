import os

os.environ.setdefault("INITIAL_ADMIN_PASSWORD", "changeme")

from app.seed import seed_admin_and_config


def test_admin_login_success_and_me(client, db_session):
    seed_admin_and_config(db_session)
    r = client.post("/api/auth/admin/login", json={"username": "admin", "password": "changeme"})
    assert r.status_code == 200
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["role"] == "admin"


def test_admin_login_bad_password(client, db_session):
    seed_admin_and_config(db_session)
    r = client.post("/api/auth/admin/login", json={"username": "admin", "password": "nope"})
    assert r.status_code == 401


def test_me_unauthenticated(client):
    assert client.get("/api/auth/me").status_code == 401
