"""Candidate-facing booking endpoints.

GET /api/slots/open       — list open slots (booked_count < capacity)
GET /api/slots/{id}/preview — prep-window preview for a slot
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config_helpers import get_config_int, get_config_str
from app.db import get_db
from app.deps import current_candidate
from app.models import Booking, Slot
from app.prep_window import build_preview

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
