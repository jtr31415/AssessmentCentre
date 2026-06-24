from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import record
from app.db import get_db
from app.deps import current_admin
from app.models import Booking, Candidate, Slot
from app.schemas import SlotCreate

router = APIRouter(prefix="/api/admin", tags=["slots"])


@router.post("/slots", status_code=status.HTTP_201_CREATED)
def create_slot(
    body: SlotCreate,
    db: Session = Depends(get_db),  # noqa: B008
    _: object = Depends(current_admin),  # noqa: B008
):
    slot = Slot(starts_at=body.starts_at, capacity=body.capacity)
    db.add(slot)
    db.commit()
    db.refresh(slot)
    booked_count = 0
    is_open = booked_count < slot.capacity
    record(
        db,
        actor="admin",
        action="slot_create",
        detail=f"slot {slot.id} @ {slot.starts_at} cap {slot.capacity}",
    )
    return {
        "id": slot.id,
        "starts_at": slot.starts_at,
        "capacity": slot.capacity,
        "booked_count": booked_count,
        "is_open": is_open,
    }


@router.get("/slots")
def list_slots(
    db: Session = Depends(get_db),  # noqa: B008
    _: object = Depends(current_admin),  # noqa: B008
):
    # Subquery: count bookings per slot
    booking_count_sq = (
        select(Booking.slot_id, func.count(Booking.id).label("cnt"))
        .group_by(Booking.slot_id)
        .subquery()
    )

    rows = db.execute(select(Slot).order_by(Slot.starts_at)).scalars().all()

    result = []
    for slot in rows:
        booked_count = (
            db.execute(
                select(func.count(Booking.id)).where(Booking.slot_id == slot.id)
            ).scalar_one()
        )
        is_open = booked_count < slot.capacity

        # Join Booking -> Candidate for candidate_id + first_name only
        booking_rows = db.execute(
            select(Candidate.candidate_id, Candidate.first_name)
            .join(Booking, Booking.candidate_id == Candidate.id)
            .where(Booking.slot_id == slot.id)
        ).all()

        bookings = [
            {"candidate_id": row.candidate_id, "first_name": row.first_name}
            for row in booking_rows
        ]

        result.append(
            {
                "id": slot.id,
                "starts_at": slot.starts_at,
                "capacity": slot.capacity,
                "booked_count": booked_count,
                "is_open": is_open,
                "bookings": bookings,
            }
        )

    return result
