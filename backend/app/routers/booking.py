"""Candidate-facing booking endpoints.

GET  /api/slots/open          — list open slots (booked_count < capacity)
GET  /api/slots/{id}/preview  — prep-window preview for a slot
POST /api/slots/{id}/book     — atomically book a slot (single-occupancy, one-per-candidate)
"""

from datetime import UTC, datetime

import sqlalchemy.exc
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import record
from app.config_helpers import get_config_int, get_config_str
from app.db import get_db
from app.deps import current_candidate
from app.models import Booking, Candidate, Slot
from app.prep_window import build_preview, compute_unlock_at

router = APIRouter(prefix="/api/slots", tags=["booking"])


@router.get("/open")
def list_open_slots(
    db: Session = Depends(get_db),  # noqa: B008
    _: object = Depends(current_candidate),  # noqa: B008
):
    """Return slots where booked_count < capacity, ordered by starts_at."""
    booked_count_subq = (
        select(func.count(Booking.id))
        .where(Booking.slot_id == Slot.id)
        .correlate(Slot)
        .scalar_subquery()
    )

    rows = (
        db.execute(
            select(Slot)
            .where(booked_count_subq < Slot.capacity)
            .order_by(Slot.starts_at)
        )
        .scalars()
        .all()
    )

    return [{"id": slot.id, "starts_at": slot.starts_at} for slot in rows]


@router.get("/{slot_id}/preview")
def slot_preview(
    slot_id: int,
    db: Session = Depends(get_db),  # noqa: B008
    _: object = Depends(current_candidate),  # noqa: B008
):
    """Return the prep-window preview for a slot.  404 if slot not found."""
    slot = db.get(Slot, slot_id)
    if slot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="slot not found")

    prep_window_days = get_config_int(db, "prep_window_days", 8)
    tz_name = get_config_str(db, "display_timezone", "Europe/London")

    return build_preview(
        slot_starts_at=slot.starts_at,
        now=datetime.now(UTC),
        prep_window_days=prep_window_days,
        tz_name=tz_name,
    )


@router.post("/{slot_id}/book", status_code=status.HTTP_201_CREATED)
def book_slot(
    slot_id: int,
    db: Session = Depends(get_db),  # noqa: B008
    cand: Candidate = Depends(current_candidate),  # noqa: B008
):
    """Atomically book a slot for the authenticated candidate.

    Uses SELECT FOR UPDATE to prevent double-booking at the DB level.
    One booking per candidate is also enforced by a UNIQUE constraint on
    Booking.candidate_id; an IntegrityError fallback catches any race.
    """
    # 1. Lock the slot row exclusively within this transaction.
    slot = db.execute(
        select(Slot).where(Slot.id == slot_id).with_for_update()
    ).scalar_one_or_none()
    if slot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="slot not found")

    # 2. Guard: candidate already has a booking (unique constraint also enforces this).
    if db.query(Booking).filter_by(candidate_id=cand.id).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="you already have a booking",
        )

    # 3. Guard: slot is at capacity.
    booked_count = db.query(Booking).filter_by(slot_id=slot_id).count()
    if booked_count >= slot.capacity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="that slot was just taken, please pick another",
        )

    # 4. Compute unlock_at and create the booking.
    now = datetime.now(UTC)
    prep_window_days = get_config_int(db, "prep_window_days", 8)
    unlock_at = compute_unlock_at(slot.starts_at, now, prep_window_days)

    # 5. Persist; catch unique-violation race as a 409 fallback.
    booking = Booking(
        candidate_id=cand.id,
        slot_id=slot_id,
        unlock_at=unlock_at,
        booked_at=now,
    )
    db.add(booking)
    try:
        db.commit()
    except sqlalchemy.exc.IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="you already have a booking",
        ) from None

    # 6. Audit (after successful commit so audit is only written on success).
    record(db, actor=cand.candidate_id, action="booking_create", detail=f"booked slot {slot_id}")

    return {
        "slot_id": slot_id,
        "unlock_at": unlock_at,
        "booked_at": now,
    }
