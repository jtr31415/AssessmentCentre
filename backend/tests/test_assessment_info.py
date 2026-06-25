"""Admin-editable assessment details + the candidate-facing assessment-info endpoint."""

from app.seed import seed_admin_and_config


def login_admin(client):
    client.post("/api/auth/admin/login", json={"username": "admin", "password": "changeme"})


def _candidate(client, db_session):
    seed_admin_and_config(db_session)
    login_admin(client)
    data = client.post("/api/admin/candidates", json={"first_name": "Ada"}).json()
    token = data["set_password_path"].split("token=")[1]
    client.post("/api/auth/candidate/set-password", json={"token": token, "password": "pw-info123"})
    client.post("/api/auth/logout")
    client.post(
        "/api/auth/candidate/login",
        json={"candidate_id": data["candidate_id"], "password": "pw-info123"},
    )
    return data["candidate_id"]


def test_admin_can_set_assessment_details(client, db_session):
    seed_admin_and_config(db_session)
    login_admin(client)
    for key, value in [
        ("assessment_format", "In person"),
        ("assessment_duration", "2 hours"),
        ("assessment_location", "Nordex HQ, Hamburg"),
    ]:
        r = client.put(f"/api/admin/config/{key}", json={"value": value})
        assert r.status_code == 200, r.text
        assert r.json()["value"] == value
    cfg = client.get("/api/admin/config").json()
    assert cfg["assessment_format"] == "In person"
    assert cfg["assessment_duration"] == "2 hours"
    assert cfg["assessment_location"] == "Nordex HQ, Hamburg"


def test_candidate_assessment_info(client, db_session):
    _candidate(client, db_session)
    r = client.get("/api/me/assessment-info")
    assert r.status_code == 200, r.text
    data = r.json()
    # Seeded defaults
    assert data["format"] == "In person"
    assert data["duration"] == ""
    assert data["location"] == ""
    assert data["prep_window_days"] == 8


def test_assessment_info_requires_candidate(client, db_session):
    seed_admin_and_config(db_session)
    assert client.get("/api/me/assessment-info").status_code == 401
