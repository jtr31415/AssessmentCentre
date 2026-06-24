"""Tests for content_manifest and content_access.

TDD: written BEFORE implementation (RED first).

DB on port 5433.
"""

# ---------------------------------------------------------------------------
# Test DB setup (port 5433 as specified)
# ---------------------------------------------------------------------------
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401  (register tables)
from app.db import Base
from app.models import Booking, Candidate, Slot

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://app:app@localhost:5433/app_test"
)


@pytest.fixture(scope="module")
def engine():
    eng = create_engine(TEST_DB_URL)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture
def db(engine):
    TestSession = sessionmaker(bind=engine, expire_on_commit=False)
    session = TestSession()
    yield session
    session.rollback()
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()
    session.close()


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
    def test_false_when_candidate_has_no_booking(self, db):
        """is_unlocked returns False when the candidate has no booking at all."""
        from app.content_access import is_unlocked

        cand = _make_candidate(db, status="active")
        assert is_unlocked(db, cand) is False

    def test_false_when_booked_but_unlock_at_is_future(self, db):
        """is_unlocked returns False when there is a booking but unlock_at is in the future."""
        from app.content_access import is_unlocked

        cand = _make_candidate(db, status="active")
        slot = _make_slot(db)
        future_unlock = datetime.now(UTC) + timedelta(hours=5)
        _make_booking(db, cand, slot, future_unlock)

        assert is_unlocked(db, cand) is False

    def test_false_when_status_not_active_even_if_booked_and_past(self, db):
        """is_unlocked returns False when status != 'active', even if booking + past unlock_at."""
        from app.content_access import is_unlocked

        cand = _make_candidate(db, status="invited")
        slot = _make_slot(db)
        past_unlock = datetime.now(UTC) - timedelta(hours=1)
        _make_booking(db, cand, slot, past_unlock)

        assert is_unlocked(db, cand) is False

    def test_true_when_active_booked_and_unlock_at_in_past(self, db):
        """is_unlocked returns True when active + has booking + unlock_at is past."""
        from app.content_access import is_unlocked

        cand = _make_candidate(db, status="active")
        slot = _make_slot(db)
        past_unlock = datetime.now(UTC) - timedelta(hours=1)
        _make_booking(db, cand, slot, past_unlock)

        assert is_unlocked(db, cand) is True


# ---------------------------------------------------------------------------
# resolve_path tests
# ---------------------------------------------------------------------------


class TestResolvePath:
    def test_returns_none_for_unknown_file_key(self, tmp_path):
        """resolve_path returns None for a file_key not in MANIFEST."""
        from app.content_manifest import resolve_path

        result = resolve_path("totally_unknown_key", str(tmp_path))
        assert result is None

    def test_returns_none_for_traversal_style_key(self, tmp_path):
        """resolve_path rejects a traversal-style key like '../config'."""
        from app.content_manifest import resolve_path

        result = resolve_path("../config", str(tmp_path))
        assert result is None

    def test_returns_none_when_file_does_not_exist_on_disk(self, tmp_path):
        """resolve_path returns None if the manifest entry's file does not exist on disk."""
        from app.content_manifest import MANIFEST, resolve_path

        # Use a real file_key but don't create the file in tmp_path
        key = MANIFEST[0]["file_key"]
        result = resolve_path(key, str(tmp_path))
        assert result is None

    def test_returns_path_for_known_key_when_file_exists(self, tmp_path):
        """resolve_path returns a real Path when the manifest file exists in content_dir."""
        from app.content_manifest import MANIFEST, resolve_path

        # Create the placeholder file in tmp_path
        entry = MANIFEST[0]
        (tmp_path / entry["filename"]).write_bytes(b"placeholder")

        result = resolve_path(entry["file_key"], str(tmp_path))
        assert result is not None
        assert isinstance(result, Path)
        assert result.is_file()

    def test_returns_none_for_another_traversal_variant(self, tmp_path):
        """resolve_path also rejects '../../etc/passwd' style keys."""
        from app.content_manifest import resolve_path

        result = resolve_path("../../etc/passwd", str(tmp_path))
        assert result is None
