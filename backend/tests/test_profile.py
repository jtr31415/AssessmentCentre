"""Tests for GET /api/me/profile — candidate profile endpoint.

TDD: written BEFORE implementation.
"""

from app.seed import seed_admin_and_config


def create_and_login_candidate(client):
    """Seed admin, create a candidate, set their password, log in as them."""
    client.post("/api/auth/admin/login", json={"username": "admin", "password": "changeme"})
    created = client.post("/api/admin/candidates", json={"first_name": "Alice"})
    assert created.status_code == 201
    data = created.json()
    token = data["set_password_path"].split("token=")[1]

    client.post(
        "/api/auth/candidate/set-password",
        json={"token": token, "password": "pw-123456"},
    )
    client.post("/api/auth/logout")
    li = client.post(
        "/api/auth/candidate/login",
        json={"candidate_id": data["candidate_id"], "password": "pw-123456"},
    )
    assert li.status_code == 200
    return data


class TestMyProfile:
    def test_logged_in_candidate_gets_200_with_correct_fields(self, client, db_session):
        """Logged-in candidate gets 200 with candidate_id, first_name, status."""
        seed_admin_and_config(db_session)
        data = create_and_login_candidate(client)

        r = client.get("/api/me/profile")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["candidate_id"] == data["candidate_id"]
        assert body["first_name"] == "Alice"
        assert "status" in body

    def test_unauthenticated_request_gets_401(self, client, db_session):
        """GET /api/me/profile returns 401 when not authenticated."""
        seed_admin_and_config(db_session)
        r = client.get("/api/me/profile")
        assert r.status_code == 401
