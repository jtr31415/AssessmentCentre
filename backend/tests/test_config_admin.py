"""Tests for GET/PUT /api/admin/config — admin config view/set.

Written BEFORE implementation (TDD / RED-first).
Uses shared db_session / client fixtures from conftest.py.
"""

import os

os.environ.setdefault("INITIAL_ADMIN_PASSWORD", "changeme")

from app.seed import seed_admin_and_config

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def login_admin(client):
    r = client.post("/api/auth/admin/login", json={"username": "admin", "password": "changeme"})
    assert r.status_code == 200, r.text


# ---------------------------------------------------------------------------
# GET /api/admin/config
# ---------------------------------------------------------------------------


class TestGetConfig:
    def test_get_config_returns_seeded_values(self, client, db_session):
        """GET returns dict containing prep_window_days == '8' and retention_date is null."""
        seed_admin_and_config(db_session)
        login_admin(client)
        r = client.get("/api/admin/config")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["prep_window_days"] == "8"
        assert data["retention_date"] is None

    def test_get_config_unauthenticated_returns_401(self, client, db_session):
        """GET without admin session → 401."""
        seed_admin_and_config(db_session)
        r = client.get("/api/admin/config")
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# PUT /api/admin/config/{key} — prep_window_days
# ---------------------------------------------------------------------------


class TestPutPrepWindowDays:
    def test_put_prep_window_days_valid(self, client, db_session):
        """PUT prep_window_days='10' → 200; GET reflects '10'."""
        seed_admin_and_config(db_session)
        login_admin(client)
        r = client.put("/api/admin/config/prep_window_days", json={"value": "10"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["key"] == "prep_window_days"
        assert body["value"] == "10"
        # Verify GET reflects the update
        get_r = client.get("/api/admin/config")
        assert get_r.json()["prep_window_days"] == "10"

    def test_put_prep_window_days_negative_returns_422(self, client, db_session):
        """PUT prep_window_days='-1' → 422."""
        seed_admin_and_config(db_session)
        login_admin(client)
        r = client.put("/api/admin/config/prep_window_days", json={"value": "-1"})
        assert r.status_code == 422, r.text

    def test_put_prep_window_days_non_int_returns_422(self, client, db_session):
        """PUT prep_window_days='abc' → 422."""
        seed_admin_and_config(db_session)
        login_admin(client)
        r = client.put("/api/admin/config/prep_window_days", json={"value": "abc"})
        assert r.status_code == 422, r.text

    def test_put_prep_window_days_unauthenticated_returns_401(self, client, db_session):
        """PUT without admin session → 401."""
        seed_admin_and_config(db_session)
        r = client.put("/api/admin/config/prep_window_days", json={"value": "5"})
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# PUT /api/admin/config/{key} — retention_date
# ---------------------------------------------------------------------------


class TestPutRetentionDate:
    def test_put_retention_date_valid_iso(self, client, db_session):
        """PUT retention_date='2026-12-31' → 200, value persists."""
        seed_admin_and_config(db_session)
        login_admin(client)
        r = client.put("/api/admin/config/retention_date", json={"value": "2026-12-31"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["key"] == "retention_date"
        assert body["value"] == "2026-12-31"
        # Verify persistence via GET
        get_r = client.get("/api/admin/config")
        assert get_r.json()["retention_date"] == "2026-12-31"

    def test_put_retention_date_empty_string_clears_to_null(self, client, db_session):
        """PUT retention_date='' → 200, value becomes null."""
        seed_admin_and_config(db_session)
        login_admin(client)
        # First set it to something
        client.put("/api/admin/config/retention_date", json={"value": "2026-12-31"})
        # Now clear it
        r = client.put("/api/admin/config/retention_date", json={"value": ""})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["key"] == "retention_date"
        assert body["value"] is None
        # Verify GET shows null
        get_r = client.get("/api/admin/config")
        assert get_r.json()["retention_date"] is None

    def test_put_retention_date_invalid_returns_422(self, client, db_session):
        """PUT retention_date='not-a-date' → 422."""
        seed_admin_and_config(db_session)
        login_admin(client)
        r = client.put("/api/admin/config/retention_date", json={"value": "not-a-date"})
        assert r.status_code == 422, r.text


# ---------------------------------------------------------------------------
# PUT /api/admin/config/{key} — display_timezone
# ---------------------------------------------------------------------------


class TestPutDisplayTimezone:
    def test_put_display_timezone_empty_string_returns_422(self, client, db_session):
        """PUT display_timezone='' → 422."""
        seed_admin_and_config(db_session)
        login_admin(client)
        r = client.put("/api/admin/config/display_timezone", json={"value": ""})
        assert r.status_code == 422, r.text

    def test_put_display_timezone_valid(self, client, db_session):
        """PUT display_timezone='Europe/London' → 200."""
        seed_admin_and_config(db_session)
        login_admin(client)
        r = client.put("/api/admin/config/display_timezone", json={"value": "Europe/London"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["key"] == "display_timezone"
        assert body["value"] == "Europe/London"


# ---------------------------------------------------------------------------
# PUT /api/admin/config/{key} — qa_sla_text
# ---------------------------------------------------------------------------


class TestPutQaSlaText:
    def test_put_qa_sla_text_valid(self, client, db_session):
        """PUT qa_sla_text → 200; GET reflects updated value."""
        seed_admin_and_config(db_session)
        login_admin(client)
        r = client.put(
            "/api/admin/config/qa_sla_text",
            json={"value": "Please respond within 24 hours"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["key"] == "qa_sla_text"
        assert body["value"] == "Please respond within 24 hours"
        # Verify GET reflects the update
        get_r = client.get("/api/admin/config")
        assert get_r.json()["qa_sla_text"] == "Please respond within 24 hours"


# ---------------------------------------------------------------------------
# PUT /api/admin/config/{key} — unknown key
# ---------------------------------------------------------------------------


class TestPutUnknownKey:
    def test_put_unknown_key_returns_400(self, client, db_session):
        """PUT unknown config key 'evil' → 400."""
        seed_admin_and_config(db_session)
        login_admin(client)
        r = client.put("/api/admin/config/evil", json={"value": "oops"})
        assert r.status_code == 400, r.text
        assert "unknown config key" in r.json()["detail"]
