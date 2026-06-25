"""The admin candidates list exposes the API key's last 4 chars (verification only)."""

from app.seed import seed_admin_and_config


def login_admin(client):
    client.post("/api/auth/admin/login", json={"username": "admin", "password": "changeme"})


def test_candidates_list_shows_api_key_last4(client, db_session):
    seed_admin_and_config(db_session)
    login_admin(client)

    cid = client.post("/api/admin/candidates", json={"first_name": "Keyed"}).json()["candidate_id"]
    r = client.put(
        f"/api/admin/candidates/{cid}/api-key",
        json={"api_key": "sk-ant-supersecretABCD"},
    )
    assert r.status_code == 200

    rows = client.get("/api/admin/candidates").json()
    row = next(c for c in rows if c["candidate_id"] == cid)
    assert row["api_key_last4"] == "ABCD"

    # A candidate with no key reports None
    cid2 = client.post("/api/admin/candidates", json={"first_name": "Keyless"}).json()[
        "candidate_id"
    ]
    rows = client.get("/api/admin/candidates").json()
    row2 = next(c for c in rows if c["candidate_id"] == cid2)
    assert row2["api_key_last4"] is None
