"""Tests for admin slot creation and status listing — TDD RED-first."""

import os

os.environ.setdefault("INITIAL_ADMIN_PASSWORD", "changeme")

from app.seed import seed_admin_and_config


def _admin_client(client, db_session):
    """Return a client that is logged in as admin."""
    seed_admin_and_config(db_session)
    r = client.post(
        "/api/auth/admin/login",
        json={"username": "admin", "password": "changeme"},
    )
    assert r.status_code == 200, r.text
    return client


class TestCreateSlot:
    def test_create_slot_returns_201_with_defaults(self, client, db_session):
        """POST /api/admin/slots returns 201 with booked_count==0, is_open==True, capacity==1."""
        c = _admin_client(client, db_session)
        payload = {"starts_at": "2026-10-15T09:00:00+00:00"}
        r = c.post("/api/admin/slots", json=payload)
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["capacity"] == 1
        assert data["booked_count"] == 0
        assert data["is_open"] is True
        assert "id" in data
        assert "starts_at" in data

    def test_create_slot_with_explicit_capacity(self, client, db_session):
        """POST /api/admin/slots with explicit capacity stores it."""
        c = _admin_client(client, db_session)
        payload = {"starts_at": "2026-10-15T09:00:00+00:00", "capacity": 5}
        r = c.post("/api/admin/slots", json=payload)
        assert r.status_code == 201, r.text
        assert r.json()["capacity"] == 5

    def test_create_slot_unauthenticated_returns_401(self, client, db_session):
        """POST /api/admin/slots without login returns 401."""
        payload = {"starts_at": "2026-10-15T09:00:00+00:00"}
        r = client.post("/api/admin/slots", json=payload)
        assert r.status_code == 401, r.text


class TestListSlots:
    def test_list_slots_returns_created_slot(self, client, db_session):
        """GET /api/admin/slots returns the slot just created."""
        c = _admin_client(client, db_session)
        c.post("/api/admin/slots", json={"starts_at": "2026-10-15T09:00:00+00:00"})
        r = c.get("/api/admin/slots")
        assert r.status_code == 200, r.text
        slots = r.json()
        assert len(slots) == 1
        slot = slots[0]
        assert slot["booked_count"] == 0
        assert slot["is_open"] is True
        assert slot["bookings"] == []

    def test_list_slots_ordered_by_starts_at(self, client, db_session):
        """GET /api/admin/slots returns slots ordered by starts_at ascending."""
        c = _admin_client(client, db_session)
        c.post("/api/admin/slots", json={"starts_at": "2026-10-20T09:00:00+00:00"})
        c.post("/api/admin/slots", json={"starts_at": "2026-10-10T09:00:00+00:00"})
        r = c.get("/api/admin/slots")
        assert r.status_code == 200, r.text
        slots = r.json()
        assert len(slots) == 2
        assert slots[0]["starts_at"] < slots[1]["starts_at"]

    def test_list_slots_unauthenticated_returns_401(self, client, db_session):
        """GET /api/admin/slots without login returns 401."""
        r = client.get("/api/admin/slots")
        assert r.status_code == 401, r.text

    def test_list_slots_with_booking_shows_booked_count_and_candidate(
        self, client, db_session
    ):
        """A slot with a booking shows booked_count==1, is_open==False, and candidate details."""
        from datetime import timedelta

        from app.models import Booking, Candidate, Slot

        c = _admin_client(client, db_session)

        # Create a slot via the API
        starts_at_str = "2026-10-15T09:00:00+00:00"
        r = c.post("/api/admin/slots", json={"starts_at": starts_at_str, "capacity": 1})
        assert r.status_code == 201
        slot_id = r.json()["id"]

        # Directly insert a Candidate and a Booking into the DB
        candidate = Candidate(
            candidate_id="C001",
            first_name="Alice",
            status="invited",
        )
        db_session.add(candidate)
        db_session.flush()

        slot_obj = db_session.get(Slot, slot_id)
        booking = Booking(
            candidate_id=candidate.id,
            slot_id=slot_obj.id,
            unlock_at=slot_obj.starts_at - timedelta(days=8),
        )
        db_session.add(booking)
        db_session.commit()

        r = c.get("/api/admin/slots")
        assert r.status_code == 200, r.text
        slots = r.json()
        assert len(slots) == 1
        slot = slots[0]
        assert slot["booked_count"] == 1
        assert slot["is_open"] is False
        bookings = slot["bookings"]
        assert len(bookings) == 1
        b = bookings[0]
        assert b["candidate_id"] == "C001"
        assert b["first_name"] == "Alice"
        # Ensure booking dict has EXACTLY the two allowed keys (no PII leakage)
        assert set(b.keys()) == {"candidate_id", "first_name"}
