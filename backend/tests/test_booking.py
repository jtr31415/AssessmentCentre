"""Tests for candidate open-slot list and booking preview endpoints.

TDD: written BEFORE implementation.

Note on concurrency: true SELECT FOR UPDATE race conditions require concurrent
connections and are omitted here as they are inherently flaky in CI.  The
capacity-guard logic is tested structurally instead.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.models import AuditLog, Booking, Candidate, Slot
from app.prep_window import compute_unlock_at
from app.seed import seed_admin_and_config

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def login_admin(client):
    client.post("/api/auth/admin/login", json={"username": "admin", "password": "changeme"})


def create_and_login_candidate(client):
    """Seed admin, create a candidate, set their password, log in as them."""
    login_admin(client)
    created = client.post("/api/admin/candidates", json={"first_name": "Test"})
    assert created.status_code == 201
    data = created.json()
    token = data["set_password_path"].split("token=")[1]

    # Set password
    client.post(
        "/api/auth/candidate/set-password",
        json={"token": token, "password": "pw-123456"},
    )
    # Log out admin, log in candidate
    client.post("/api/auth/logout")
    li = client.post(
        "/api/auth/candidate/login",
        json={"candidate_id": data["candidate_id"], "password": "pw-123456"},
    )
    assert li.status_code == 200
    client.post("/api/me/nda/accept")  # accept NDA at first login (gates participation)
    return data["candidate_id"]


def admin_create_slot(client, starts_at: datetime, capacity: int = 1) -> int:
    """Create a slot as admin; returns slot id. Caller must be logged in as admin."""
    r = client.post(
        "/api/admin/slots",
        json={"starts_at": starts_at.isoformat(), "capacity": capacity},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ---------------------------------------------------------------------------
# /api/slots/open
# ---------------------------------------------------------------------------

class TestOpenSlots:
    def test_requires_candidate_auth(self, client, db_session):
        """GET /api/slots/open must return 401 when not authenticated."""
        seed_admin_and_config(db_session)
        r = client.get("/api/slots/open")
        assert r.status_code == 401

    def test_excludes_full_slot_includes_open_slot(self, client, db_session):
        """Open-slot list excludes capacity-1 slot with a booking, includes open slot."""
        seed_admin_and_config(db_session)

        # Create candidate and log in
        candidate_id = create_and_login_candidate(client)

        # Now create slots as admin (need to re-auth as admin temporarily)
        client.post("/api/auth/logout")
        login_admin(client)

        future = datetime.now(UTC) + timedelta(days=30)
        full_slot_id = admin_create_slot(client, future + timedelta(hours=1), capacity=1)
        open_slot_id = admin_create_slot(client, future + timedelta(hours=2), capacity=1)

        # Create a booking for the full slot using the DB directly
        cand_row = db_session.execute(
            select(Candidate).where(Candidate.candidate_id == candidate_id)
        ).scalar_one()

        booking = Booking(
            candidate_id=cand_row.id,
            slot_id=full_slot_id,
            unlock_at=datetime.now(UTC),
        )
        db_session.add(booking)
        db_session.commit()

        # Log back in as candidate
        client.post("/api/auth/logout")
        li = client.post(
            "/api/auth/candidate/login",
            json={"candidate_id": candidate_id, "password": "pw-123456"},
        )
        assert li.status_code == 200

        r = client.get("/api/slots/open")
        assert r.status_code == 200
        ids = [s["id"] for s in r.json()]
        assert full_slot_id not in ids, "Full slot should be excluded"
        assert open_slot_id in ids, "Open slot should be included"

    def test_excludes_partially_booked_multi_capacity_slot(self, client, db_session):
        """A capacity-2 slot with ONE booking must NOT appear to other candidates.

        Candidates must never see a slot that anyone else has booked, so that
        they cannot infer how many other candidates are in the running.
        """
        seed_admin_and_config(db_session)

        # Candidate A books one seat of a 2-capacity slot.
        cand_a_id = create_and_login_candidate(client)
        client.post("/api/auth/logout")
        login_admin(client)
        future = datetime.now(UTC) + timedelta(days=30)
        shared_slot_id = admin_create_slot(client, future + timedelta(hours=1), capacity=2)
        empty_slot_id = admin_create_slot(client, future + timedelta(hours=2), capacity=2)

        client.post("/api/auth/logout")
        client.post(
            "/api/auth/candidate/login",
            json={"candidate_id": cand_a_id, "password": "pw-123456"},
        )
        r = client.post(f"/api/slots/{shared_slot_id}/book")
        assert r.status_code == 201, r.text

        # Candidate B must not see the slot A booked, even though a seat remains.
        _second_candidate(client, db_session)
        r = client.get("/api/slots/open")
        assert r.status_code == 200
        ids = [s["id"] for s in r.json()]
        assert shared_slot_id not in ids, "Partially-booked slot must be hidden from others"
        assert empty_slot_id in ids, "A slot with no bookings must still be visible"

    def test_response_shape(self, client, db_session):
        """Each slot in the list has id and starts_at."""
        seed_admin_and_config(db_session)
        candidate_id = create_and_login_candidate(client)

        # Create a slot as admin
        client.post("/api/auth/logout")
        login_admin(client)
        future = datetime.now(UTC) + timedelta(days=10)
        admin_create_slot(client, future)

        # Log back in as candidate
        client.post("/api/auth/logout")
        client.post(
            "/api/auth/candidate/login",
            json={"candidate_id": candidate_id, "password": "pw-123456"},
        )

        r = client.get("/api/slots/open")
        assert r.status_code == 200
        slots = r.json()
        assert len(slots) >= 1
        for s in slots:
            assert "id" in s
            assert "starts_at" in s


# ---------------------------------------------------------------------------
# /api/slots/{slot_id}/preview
# ---------------------------------------------------------------------------

class TestSlotPreview:
    def _login_as_candidate(self, client, db_session):
        seed_admin_and_config(db_session)
        return create_and_login_candidate(client)

    def _create_slot_as_admin(self, client, starts_at: datetime) -> int:
        """Switch to admin, create slot, switch back to candidate."""
        client.post("/api/auth/logout")
        login_admin(client)
        slot_id = admin_create_slot(client, starts_at)
        client.post("/api/auth/logout")
        return slot_id

    def test_preview_slot_20_days_out(self, client, db_session):
        """Slot 20 days out, prep_window_days=8 → prep_days=8.0, unlocks_immediately=False."""
        candidate_id = self._login_as_candidate(client, db_session)

        future = datetime.now(UTC) + timedelta(days=20)
        slot_id = self._create_slot_as_admin(client, future)

        client.post(
            "/api/auth/candidate/login",
            json={"candidate_id": candidate_id, "password": "pw-123456"},
        )

        r = client.get(f"/api/slots/{slot_id}/preview")
        assert r.status_code == 200
        data = r.json()
        assert data["prep_days"] == 8.0
        assert data["unlocks_immediately"] is False
        # Check all required keys are present
        for key in (
            "assessment_at_iso",
            "unlock_at_iso",
            "prep_days",
            "assessment_display",
            "unlock_display",
            "unlocks_immediately",
        ):
            assert key in data, f"Missing key: {key}"

    def test_preview_slot_2_days_out(self, client, db_session):
        """Slot 2 days out, prep_window_days=8 → prep_days≈2.0, unlocks_immediately=True."""
        candidate_id = self._login_as_candidate(client, db_session)

        future = datetime.now(UTC) + timedelta(days=2)
        slot_id = self._create_slot_as_admin(client, future)

        client.post(
            "/api/auth/candidate/login",
            json={"candidate_id": candidate_id, "password": "pw-123456"},
        )

        r = client.get(f"/api/slots/{slot_id}/preview")
        assert r.status_code == 200
        data = r.json()
        # prep_days should be approximately 2.0 (slot is 2 days away, window=8 → unlocks now)
        assert 1.9 <= data["prep_days"] <= 2.1, f"Expected ~2.0, got {data['prep_days']}"
        assert data["unlocks_immediately"] is True

    def test_preview_404_for_missing_slot(self, client, db_session):
        """Preview of a non-existent slot returns 404."""
        seed_admin_and_config(db_session)
        create_and_login_candidate(client)

        r = client.get("/api/slots/99999/preview")
        assert r.status_code == 404

    def test_preview_requires_candidate_auth(self, client, db_session):
        """Preview endpoint returns 401 when not authenticated."""
        seed_admin_and_config(db_session)
        r = client.get("/api/slots/1/preview")
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/slots/{slot_id}/book
# ---------------------------------------------------------------------------

def _second_candidate(client, db_session):
    """Create a *second* candidate (admin must already be seeded). Returns candidate_id str."""
    client.post("/api/auth/logout")
    login_admin(client)
    created = client.post("/api/admin/candidates", json={"first_name": "Second"})
    assert created.status_code == 201
    data = created.json()
    token = data["set_password_path"].split("token=")[1]
    client.post(
        "/api/auth/candidate/set-password",
        json={"token": token, "password": "pw-second1"},
    )
    client.post("/api/auth/logout")
    li = client.post(
        "/api/auth/candidate/login",
        json={"candidate_id": data["candidate_id"], "password": "pw-second1"},
    )
    assert li.status_code == 200
    client.post("/api/me/nda/accept")  # accept NDA at first login (gates participation)
    return data["candidate_id"]


class TestBookSlot:
    def test_happy_path_returns_201_with_correct_shape(self, client, db_session):
        """Candidate books an open slot → 201 with slot_id, unlock_at, booked_at."""
        seed_admin_and_config(db_session)
        candidate_id = create_and_login_candidate(client)

        # Create slot as admin
        client.post("/api/auth/logout")
        login_admin(client)
        future = datetime.now(UTC) + timedelta(days=20)
        slot_id = admin_create_slot(client, future, capacity=1)

        # Log back in as candidate
        client.post("/api/auth/logout")
        client.post(
            "/api/auth/candidate/login",
            json={"candidate_id": candidate_id, "password": "pw-123456"},
        )

        r = client.post(f"/api/slots/{slot_id}/book")
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["slot_id"] == slot_id
        assert "unlock_at" in data
        assert "booked_at" in data

    def test_happy_path_booking_row_exists_with_correct_unlock_at(self, client, db_session):
        """After booking, a Booking row exists with unlock_at matching compute_unlock_at."""
        seed_admin_and_config(db_session)
        candidate_id = create_and_login_candidate(client)

        # Create slot as admin
        client.post("/api/auth/logout")
        login_admin(client)
        future = datetime.now(UTC) + timedelta(days=20)
        slot_id = admin_create_slot(client, future, capacity=1)

        # Log back in as candidate and book
        client.post("/api/auth/logout")
        client.post(
            "/api/auth/candidate/login",
            json={"candidate_id": candidate_id, "password": "pw-123456"},
        )
        r = client.post(f"/api/slots/{slot_id}/book")
        assert r.status_code == 201, r.text

        # Verify the booking row in the DB
        cand_row = db_session.execute(
            select(Candidate).where(Candidate.candidate_id == candidate_id)
        ).scalar_one()
        booking = db_session.execute(
            select(Booking).where(Booking.candidate_id == cand_row.id)
        ).scalar_one_or_none()
        assert booking is not None, "Booking row must exist"
        assert booking.slot_id == slot_id

        # unlock_at must match compute_unlock_at(slot.starts_at, booked_at, prep_window_days=8)
        expected_unlock = compute_unlock_at(future, booking.booked_at, 8)
        # Allow 2-second tolerance for clock drift in test
        assert abs((booking.unlock_at - expected_unlock).total_seconds()) < 2

    def test_happy_path_audit_row_booking_create_exists(self, client, db_session):
        """After booking, an audit row with action='booking_create' exists."""
        seed_admin_and_config(db_session)
        candidate_id = create_and_login_candidate(client)

        client.post("/api/auth/logout")
        login_admin(client)
        future = datetime.now(UTC) + timedelta(days=20)
        slot_id = admin_create_slot(client, future, capacity=1)

        client.post("/api/auth/logout")
        client.post(
            "/api/auth/candidate/login",
            json={"candidate_id": candidate_id, "password": "pw-123456"},
        )
        r = client.post(f"/api/slots/{slot_id}/book")
        assert r.status_code == 201, r.text

        audit = db_session.execute(
            select(AuditLog).where(
                AuditLog.action == "booking_create",
                AuditLog.actor == candidate_id,
            )
        ).scalar_one_or_none()
        assert audit is not None, "audit_log row for booking_create must exist"

    def test_one_per_candidate_second_booking_returns_409(self, client, db_session):
        """Same candidate books a second (different) slot → 409 'you already have a booking'."""
        seed_admin_and_config(db_session)
        candidate_id = create_and_login_candidate(client)

        client.post("/api/auth/logout")
        login_admin(client)
        future = datetime.now(UTC) + timedelta(days=20)
        slot1_id = admin_create_slot(client, future + timedelta(hours=1), capacity=2)
        slot2_id = admin_create_slot(client, future + timedelta(hours=2), capacity=2)

        client.post("/api/auth/logout")
        client.post(
            "/api/auth/candidate/login",
            json={"candidate_id": candidate_id, "password": "pw-123456"},
        )

        r1 = client.post(f"/api/slots/{slot1_id}/book")
        assert r1.status_code == 201, r1.text

        r2 = client.post(f"/api/slots/{slot2_id}/book")
        assert r2.status_code == 409, r2.text
        assert "already have a booking" in r2.json()["detail"]

    def test_capacity_full_returns_409(self, client, db_session):
        """Capacity-1 slot: candidate A books → 201; candidate B books same slot → 409."""
        seed_admin_and_config(db_session)

        # Candidate A
        cand_a_id = create_and_login_candidate(client)

        # Create slot as admin
        client.post("/api/auth/logout")
        login_admin(client)
        future = datetime.now(UTC) + timedelta(days=20)
        slot_id = admin_create_slot(client, future, capacity=1)

        # Candidate A books
        client.post("/api/auth/logout")
        client.post(
            "/api/auth/candidate/login",
            json={"candidate_id": cand_a_id, "password": "pw-123456"},
        )
        r1 = client.post(f"/api/slots/{slot_id}/book")
        assert r1.status_code == 201, r1.text

        # Candidate B attempts same slot
        _second_candidate(client, db_session)
        r2 = client.post(f"/api/slots/{slot_id}/book")
        assert r2.status_code == 409, r2.text
        assert "just taken" in r2.json()["detail"]

    def test_book_missing_slot_returns_404(self, client, db_session):
        """Booking a non-existent slot → 404."""
        seed_admin_and_config(db_session)
        candidate_id = create_and_login_candidate(client)

        client.post("/api/auth/logout")
        client.post(
            "/api/auth/candidate/login",
            json={"candidate_id": candidate_id, "password": "pw-123456"},
        )

        r = client.post("/api/slots/99999/book")
        assert r.status_code == 404, r.text

    def test_book_requires_candidate_auth(self, client, db_session):
        """Booking endpoint returns 401 when not authenticated."""
        seed_admin_and_config(db_session)
        r = client.post("/api/slots/1/book")
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/admin/bookings/reassign
# ---------------------------------------------------------------------------

class TestAdminReassign:
    def _setup(self, client, db_session):
        """Seed config, create a candidate with a booking, return useful IDs."""
        seed_admin_and_config(db_session)
        candidate_id = create_and_login_candidate(client)

        # Create two slots as admin
        client.post("/api/auth/logout")
        login_admin(client)
        future = datetime.now(UTC) + timedelta(days=20)
        slot1_id = admin_create_slot(client, future + timedelta(hours=1), capacity=2)
        slot2_id = admin_create_slot(client, future + timedelta(hours=10), capacity=2)

        # Book slot1 as candidate
        client.post("/api/auth/logout")
        client.post(
            "/api/auth/candidate/login",
            json={"candidate_id": candidate_id, "password": "pw-123456"},
        )
        r = client.post(f"/api/slots/{slot1_id}/book")
        assert r.status_code == 201, r.text

        # Return to admin session
        client.post("/api/auth/logout")
        login_admin(client)
        return candidate_id, slot1_id, slot2_id

    def test_reassign_moves_booking_and_recomputes_unlock_at(self, client, db_session):
        """Reassign moves the booking to the new slot; unlock_at is recomputed."""
        candidate_id, slot1_id, slot2_id = self._setup(client, db_session)

        r = client.post(
            "/api/admin/bookings/reassign",
            json={"candidate_id": candidate_id, "new_slot_id": slot2_id},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["candidate_id"] == candidate_id
        assert data["slot_id"] == slot2_id
        assert "unlock_at" in data

        # Verify DB: booking points to new slot
        cand_row = db_session.execute(
            select(Candidate).where(Candidate.candidate_id == candidate_id)
        ).scalar_one()
        booking = db_session.execute(
            select(Booking).where(Booking.candidate_id == cand_row.id)
        ).scalar_one()
        assert booking.slot_id == slot2_id

        # unlock_at should be based on new slot's starts_at, not old slot
        new_slot = db_session.get(Slot, slot2_id)
        old_slot = db_session.get(Slot, slot1_id)
        expected_unlock = compute_unlock_at(new_slot.starts_at, booking.booked_at, 8)
        old_unlock = compute_unlock_at(old_slot.starts_at, booking.booked_at, 8)
        assert abs((booking.unlock_at - expected_unlock).total_seconds()) < 2
        # The new slot is further out so unlock_at should differ from old
        assert abs((booking.unlock_at - old_unlock).total_seconds()) > 60

    def test_reassign_old_slot_becomes_open(self, client, db_session):
        """After reassign, the old slot should appear in /api/slots/open."""
        candidate_id, slot1_id, slot2_id = self._setup(client, db_session)

        # slot1 has capacity=2 and only 1 booking — it was open before too.
        # Test with capacity=1 slots so we can see it becoming open.
        # Create fresh capacity-1 slots for this test.
        future = datetime.now(UTC) + timedelta(days=20)
        slot_a_id = admin_create_slot(client, future + timedelta(hours=5), capacity=1)
        slot_b_id = admin_create_slot(client, future + timedelta(hours=6), capacity=1)

        # Book slot_a as the same candidate (need fresh candidate)
        client.post("/api/auth/logout")
        candidate_id2 = create_and_login_candidate(client)
        r = client.post(f"/api/slots/{slot_a_id}/book")
        assert r.status_code == 201, r.text

        # slot_a is now full; reassign as admin
        client.post("/api/auth/logout")
        login_admin(client)
        r = client.post(
            "/api/admin/bookings/reassign",
            json={"candidate_id": candidate_id2, "new_slot_id": slot_b_id},
        )
        assert r.status_code == 200, r.text

        # slot_a should now appear open when candidate logs in
        client.post("/api/auth/logout")
        client.post(
            "/api/auth/candidate/login",
            json={"candidate_id": candidate_id2, "password": "pw-123456"},
        )
        r = client.get("/api/slots/open")
        assert r.status_code == 200
        ids = [s["id"] for s in r.json()]
        assert slot_a_id in ids, "Old slot should be open again after reassign"

    def test_reassign_into_full_slot_returns_409(self, client, db_session):
        """Reassign into a full (capacity=1) slot → 409 'that slot is full'."""
        seed_admin_and_config(db_session)

        # Candidate A has a booking
        cand_a_id = create_and_login_candidate(client)
        client.post("/api/auth/logout")
        login_admin(client)
        future = datetime.now(UTC) + timedelta(days=20)
        slot1_id = admin_create_slot(client, future + timedelta(hours=1), capacity=2)
        slot_full_id = admin_create_slot(client, future + timedelta(hours=2), capacity=1)

        client.post("/api/auth/logout")
        client.post(
            "/api/auth/candidate/login",
            json={"candidate_id": cand_a_id, "password": "pw-123456"},
        )
        r = client.post(f"/api/slots/{slot1_id}/book")
        assert r.status_code == 201, r.text

        # Candidate B fills slot_full
        _second_candidate(client, db_session)
        r = client.post(f"/api/slots/{slot_full_id}/book")
        assert r.status_code == 201, r.text

        # Admin tries to reassign cand_a to full slot
        client.post("/api/auth/logout")
        login_admin(client)
        r = client.post(
            "/api/admin/bookings/reassign",
            json={"candidate_id": cand_a_id, "new_slot_id": slot_full_id},
        )
        assert r.status_code == 409, r.text
        assert "full" in r.json()["detail"]

    def test_reassign_unknown_candidate_returns_404(self, client, db_session):
        """Reassign for a candidate_id that doesn't exist → 404."""
        seed_admin_and_config(db_session)
        login_admin(client)
        r = client.post(
            "/api/admin/bookings/reassign",
            json={"candidate_id": "DOES-NOT-EXIST", "new_slot_id": 1},
        )
        assert r.status_code == 404, r.text

    def test_reassign_candidate_with_no_booking_returns_404(self, client, db_session):
        """Reassign for a candidate who has no booking → 404."""
        seed_admin_and_config(db_session)
        candidate_id = create_and_login_candidate(client)
        client.post("/api/auth/logout")
        login_admin(client)

        future = datetime.now(UTC) + timedelta(days=20)
        slot_id = admin_create_slot(client, future)

        r = client.post(
            "/api/admin/bookings/reassign",
            json={"candidate_id": candidate_id, "new_slot_id": slot_id},
        )
        assert r.status_code == 404, r.text
        assert "no booking" in r.json()["detail"]

    def test_reassign_unknown_new_slot_returns_404(self, client, db_session):
        """Reassign to a slot that doesn't exist → 404."""
        candidate_id, slot1_id, slot2_id = self._setup(client, db_session)

        r = client.post(
            "/api/admin/bookings/reassign",
            json={"candidate_id": candidate_id, "new_slot_id": 99999},
        )
        assert r.status_code == 404, r.text

    def test_reassign_requires_admin_auth(self, client, db_session):
        """Reassign endpoint returns 401 for non-admin callers."""
        seed_admin_and_config(db_session)
        # Not logged in at all
        r = client.post(
            "/api/admin/bookings/reassign",
            json={"candidate_id": "x", "new_slot_id": 1},
        )
        assert r.status_code == 401

    def test_reassign_audit_row_exists(self, client, db_session):
        """After reassign, an audit row with action='booking_reassign' exists."""
        candidate_id, slot1_id, slot2_id = self._setup(client, db_session)

        r = client.post(
            "/api/admin/bookings/reassign",
            json={"candidate_id": candidate_id, "new_slot_id": slot2_id},
        )
        assert r.status_code == 200, r.text

        audit = db_session.execute(
            select(AuditLog).where(AuditLog.action == "booking_reassign")
        ).scalar_one_or_none()
        assert audit is not None, "audit_log row for booking_reassign must exist"


# ---------------------------------------------------------------------------
# POST /api/admin/bookings/release
# ---------------------------------------------------------------------------

class TestAdminRelease:
    def _setup_with_booking(self, client, db_session):
        """Seed, create candidate with booking; return as admin session."""
        seed_admin_and_config(db_session)
        candidate_id = create_and_login_candidate(client)

        client.post("/api/auth/logout")
        login_admin(client)
        future = datetime.now(UTC) + timedelta(days=20)
        slot_id = admin_create_slot(client, future, capacity=1)

        client.post("/api/auth/logout")
        client.post(
            "/api/auth/candidate/login",
            json={"candidate_id": candidate_id, "password": "pw-123456"},
        )
        r = client.post(f"/api/slots/{slot_id}/book")
        assert r.status_code == 201, r.text

        client.post("/api/auth/logout")
        login_admin(client)
        return candidate_id, slot_id

    def test_release_removes_booking(self, client, db_session):
        """Release deletes the booking and returns {ok: true}."""
        candidate_id, slot_id = self._setup_with_booking(client, db_session)

        r = client.post(
            "/api/admin/bookings/release",
            json={"candidate_id": candidate_id},
        )
        assert r.status_code == 200, r.text
        assert r.json() == {"ok": True}

        # Booking row should be gone
        cand_row = db_session.execute(
            select(Candidate).where(Candidate.candidate_id == candidate_id)
        ).scalar_one()
        booking = db_session.execute(
            select(Booking).where(Booking.candidate_id == cand_row.id)
        ).scalar_one_or_none()
        assert booking is None, "Booking should be deleted after release"

    def test_release_slot_appears_open_again(self, client, db_session):
        """After release, the freed slot appears in /api/slots/open."""
        candidate_id, slot_id = self._setup_with_booking(client, db_session)

        r = client.post(
            "/api/admin/bookings/release",
            json={"candidate_id": candidate_id},
        )
        assert r.status_code == 200, r.text

        # Log in as the same candidate to check open slots
        client.post("/api/auth/logout")
        client.post(
            "/api/auth/candidate/login",
            json={"candidate_id": candidate_id, "password": "pw-123456"},
        )
        r = client.get("/api/slots/open")
        assert r.status_code == 200
        ids = [s["id"] for s in r.json()]
        assert slot_id in ids, "Released slot should appear open again"

    def test_release_no_booking_returns_404(self, client, db_session):
        """Release a candidate who has no booking → 404."""
        seed_admin_and_config(db_session)
        candidate_id = create_and_login_candidate(client)
        client.post("/api/auth/logout")
        login_admin(client)

        r = client.post(
            "/api/admin/bookings/release",
            json={"candidate_id": candidate_id},
        )
        assert r.status_code == 404, r.text

    def test_release_unknown_candidate_returns_404(self, client, db_session):
        """Release for unknown candidate_id → 404."""
        seed_admin_and_config(db_session)
        login_admin(client)

        r = client.post(
            "/api/admin/bookings/release",
            json={"candidate_id": "DOES-NOT-EXIST"},
        )
        assert r.status_code == 404, r.text

    def test_release_requires_admin_auth(self, client, db_session):
        """Release endpoint returns 401 for non-admin callers."""
        seed_admin_and_config(db_session)
        r = client.post(
            "/api/admin/bookings/release",
            json={"candidate_id": "x"},
        )
        assert r.status_code == 401

    def test_release_audit_row_exists(self, client, db_session):
        """After release, an audit row with action='booking_release' exists."""
        candidate_id, slot_id = self._setup_with_booking(client, db_session)

        r = client.post(
            "/api/admin/bookings/release",
            json={"candidate_id": candidate_id},
        )
        assert r.status_code == 200, r.text

        audit = db_session.execute(
            select(AuditLog).where(AuditLog.action == "booking_release")
        ).scalar_one_or_none()
        assert audit is not None, "audit_log row for booking_release must exist"


# ---------------------------------------------------------------------------
# GET /api/me/booking
# ---------------------------------------------------------------------------

class TestMyBooking:
    def test_no_booking_returns_has_booking_false(self, client, db_session):
        """Candidate with no booking → {has_booking: false}."""
        seed_admin_and_config(db_session)
        create_and_login_candidate(client)

        r = client.get("/api/me/booking")
        assert r.status_code == 200, r.text
        assert r.json() == {"has_booking": False}

    def test_after_booking_returns_has_booking_true_with_correct_fields(self, client, db_session):
        """After booking, response has has_booking=true, slot_starts_at, unlock_at."""
        seed_admin_and_config(db_session)
        candidate_id = create_and_login_candidate(client)

        # Create slot + book it
        client.post("/api/auth/logout")
        login_admin(client)
        future = datetime.now(UTC) + timedelta(days=20)
        slot_id = admin_create_slot(client, future, capacity=1)

        client.post("/api/auth/logout")
        client.post(
            "/api/auth/candidate/login",
            json={"candidate_id": candidate_id, "password": "pw-123456"},
        )
        r = client.post(f"/api/slots/{slot_id}/book")
        assert r.status_code == 201, r.text

        r = client.get("/api/me/booking")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["has_booking"] is True
        assert "slot_starts_at" in data
        assert "unlock_at" in data
        assert "unlocked" in data

    def test_unlocked_false_when_unlock_at_is_future(self, client, db_session):
        """With unlock_at 20 days in the future, unlocked should be False."""
        seed_admin_and_config(db_session)
        candidate_id = create_and_login_candidate(client)

        client.post("/api/auth/logout")
        login_admin(client)
        future = datetime.now(UTC) + timedelta(days=20)
        slot_id = admin_create_slot(client, future, capacity=1)

        client.post("/api/auth/logout")
        client.post(
            "/api/auth/candidate/login",
            json={"candidate_id": candidate_id, "password": "pw-123456"},
        )
        client.post(f"/api/slots/{slot_id}/book")

        r = client.get("/api/me/booking")
        assert r.status_code == 200, r.text
        assert r.json()["unlocked"] is False

    def test_unlocked_true_when_unlock_at_is_past(self, client, db_session):
        """Booking with past unlock_at → unlocked=True."""
        from sqlalchemy import select as sa_select
        seed_admin_and_config(db_session)
        candidate_id = create_and_login_candidate(client)

        client.post("/api/auth/logout")
        login_admin(client)
        # Slot 2 days away → unlock_at == now (unlocks immediately)
        future = datetime.now(UTC) + timedelta(days=2)
        slot_id = admin_create_slot(client, future, capacity=1)

        client.post("/api/auth/logout")
        client.post(
            "/api/auth/candidate/login",
            json={"candidate_id": candidate_id, "password": "pw-123456"},
        )
        client.post(f"/api/slots/{slot_id}/book")

        # Force unlock_at to a past time in DB
        from app.models import Booking as BookModel
        from app.models import Candidate as CandModel
        cand_row = db_session.execute(
            sa_select(CandModel).where(CandModel.candidate_id == candidate_id)
        ).scalar_one()
        booking = db_session.execute(
            sa_select(BookModel).where(BookModel.candidate_id == cand_row.id)
        ).scalar_one()
        booking.unlock_at = datetime.now(UTC) - timedelta(hours=1)
        db_session.commit()

        r = client.get("/api/me/booking")
        assert r.status_code == 200, r.text
        assert r.json()["unlocked"] is True

    def test_requires_candidate_auth(self, client, db_session):
        """GET /api/me/booking returns 401 when not authenticated."""
        seed_admin_and_config(db_session)
        r = client.get("/api/me/booking")
        assert r.status_code == 401
