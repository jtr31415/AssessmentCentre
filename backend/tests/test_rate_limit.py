"""Login brute-force guard: too many failed attempts → 429; success resets."""

from app.seed import seed_admin_and_config


def test_login_rate_limited_after_failures(client, db_session):
    seed_admin_and_config(db_session)
    for _ in range(10):
        r = client.post("/api/auth/admin/login", json={"username": "admin", "password": "wrong"})
        assert r.status_code == 401
    # 11th attempt is blocked
    r = client.post("/api/auth/admin/login", json={"username": "admin", "password": "wrong"})
    assert r.status_code == 429


def test_successful_login_resets_counter(client, db_session):
    seed_admin_and_config(db_session)
    for _ in range(5):
        client.post("/api/auth/admin/login", json={"username": "admin", "password": "wrong"})
    # A correct login succeeds and resets the failure counter
    r = client.post("/api/auth/admin/login", json={"username": "admin", "password": "changeme"})
    assert r.status_code == 200
    # Counter is fresh — the next wrong attempt is a plain 401, not 429
    r = client.post("/api/auth/admin/login", json={"username": "admin", "password": "wrong"})
    assert r.status_code == 401
