"""Tests for content_access (unlock gating) and content_storage (path safety).

Uses the shared ``db_session`` fixture from conftest.py (do NOT define a local
engine fixture — a module-scoped engine that drops_all on teardown would destroy
the shared test schema for every later test module).
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.models import Booking, Candidate, Slot

# ---------------------------------------------------------------------------
# Helpers to build model instances
# ---------------------------------------------------------------------------


def _make_candidate(db, status: str = "active") -> Candidate:
    cand = Candidate(
        candidate_id=f"TST-{datetime.now(UTC).timestamp():.0f}",
        first_name="Test",
        status=status,
    )
    db.add(cand)
    db.flush()
    return cand


def _make_slot(db) -> Slot:
    slot = Slot(starts_at=datetime.now(UTC) + timedelta(days=10))
    db.add(slot)
    db.flush()
    return slot


def _make_booking(db, candidate: Candidate, slot: Slot, unlock_at: datetime) -> Booking:
    booking = Booking(
        candidate_id=candidate.id,
        slot_id=slot.id,
        unlock_at=unlock_at,
    )
    db.add(booking)
    db.flush()
    return booking


# ---------------------------------------------------------------------------
# is_unlocked tests
# ---------------------------------------------------------------------------


class TestIsUnlocked:
    def test_false_when_candidate_has_no_booking(self, db_session):
        """is_unlocked returns False when the candidate has no booking at all."""
        from app.content_access import is_unlocked

        cand = _make_candidate(db_session, status="active")
        assert is_unlocked(db_session, cand) is False

    def test_false_when_booked_but_unlock_at_is_future(self, db_session):
        """is_unlocked returns False when there is a booking but unlock_at is in the future."""
        from app.content_access import is_unlocked

        cand = _make_candidate(db_session, status="active")
        slot = _make_slot(db_session)
        future_unlock = datetime.now(UTC) + timedelta(hours=5)
        _make_booking(db_session, cand, slot, future_unlock)

        assert is_unlocked(db_session, cand) is False

    def test_false_when_status_not_active_even_if_booked_and_past(self, db_session):
        """is_unlocked returns False when status != 'active', even if booking + past unlock_at."""
        from app.content_access import is_unlocked

        cand = _make_candidate(db_session, status="invited")
        slot = _make_slot(db_session)
        past_unlock = datetime.now(UTC) - timedelta(hours=1)
        _make_booking(db_session, cand, slot, past_unlock)

        assert is_unlocked(db_session, cand) is False

    def test_true_when_active_booked_and_unlock_at_in_past(self, db_session):
        """is_unlocked returns True when active + has booking + unlock_at is past."""
        from app.content_access import is_unlocked

        cand = _make_candidate(db_session, status="active")
        slot = _make_slot(db_session)
        past_unlock = datetime.now(UTC) - timedelta(hours=1)
        _make_booking(db_session, cand, slot, past_unlock)

        assert is_unlocked(db_session, cand) is True


# ---------------------------------------------------------------------------
# content_storage path-safety tests
# ---------------------------------------------------------------------------


class TestSafeExtension:
    def test_simple_extension(self):
        from app.content_storage import safe_extension

        assert safe_extension("brief.PDF") == ".pdf"

    def test_no_extension_returns_empty(self):
        from app.content_storage import safe_extension

        assert safe_extension("README") == ""

    def test_traversal_and_weird_names_collapse(self):
        from app.content_storage import safe_extension

        # No clean alphanumeric suffix → empty (never produces a path separator).
        assert safe_extension("../../etc/passwd") == ""
        assert safe_extension("evil.") == ""


class TestStoredFilename:
    def test_stored_filename_is_hex_key_plus_ext(self):
        from app.content_storage import allocate_file_key, stored_filename_for

        key = allocate_file_key()
        assert len(key) == 32
        assert stored_filename_for(key, "turbine.csv") == f"{key}.csv"
        assert stored_filename_for(key, "noext") == key


class TestResolveStoredPath:
    def test_rejects_non_whitelisted_name(self, tmp_path):
        from app.content_storage import resolve_stored_path

        # A traversal-style name never matches the strict <hex>[.ext] whitelist.
        (tmp_path / "secret").write_bytes(b"x")
        assert resolve_stored_path("../secret", str(tmp_path)) is None
        assert resolve_stored_path("not-a-key.txt", str(tmp_path)) is None

    def test_returns_none_when_file_missing(self, tmp_path):
        from app.content_storage import allocate_file_key, resolve_stored_path

        stored = f"{allocate_file_key()}.pdf"
        assert resolve_stored_path(stored, str(tmp_path)) is None

    def test_returns_path_when_file_exists(self, tmp_path):
        from app.content_storage import allocate_file_key, resolve_stored_path

        stored = f"{allocate_file_key()}.pdf"
        (tmp_path / stored).write_bytes(b"placeholder")

        result = resolve_stored_path(stored, str(tmp_path))
        assert result is not None
        assert isinstance(result, Path)
        assert result.is_file()
