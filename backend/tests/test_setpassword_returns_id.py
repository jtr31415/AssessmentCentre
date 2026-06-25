"""set-password returns the candidate_id so the UI can show it to the candidate."""

from app.seed import seed_admin_and_config


def test_set_password_returns_candidate_id(client, db_session):
    seed_admin_and_config(db_session)
    client.post("/api/auth/admin/login", json={"username": "admin", "password": "changeme"})

    created = client.post("/api/admin/candidates", json={"first_name": "IDTester"})
    assert created.status_code == 201
    data = created.json()
    token = data["set_password_path"].split("token=")[1]

    r = client.post(
        "/api/auth/candidate/set-password",
        json={"token": token, "password": "pw-Testing1"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["candidate_id"] == data["candidate_id"]
