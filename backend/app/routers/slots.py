from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import record
from app.db import get_db
from app.deps import current_admin
from app.models import Booking, Candidate, Slot
from app.schemas import SlotCreate, SlotUpdate

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


_BOOKED_MSG = "slot is booked; reassign or release first"


def _get_slot_or_404(slot_id: int, db: Session) -> Slot:
    slot = db.get(Slot, slot_id)
    if slot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="slot not found")
    return slot


def _assert_unbooked(slot_id: int, db: Session) -> None:
    if db.query(Booking).filter_by(slot_id=slot_id).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_BOOKED_MSG)


@router.patch("/slots/{slot_id}")
def update_slot(
    slot_id: int,
    body: SlotUpdate,
    db: Session = Depends(get_db),  # noqa: B008
    _: object = Depends(current_admin),  # noqa: B008
):
    slot = _get_slot_or_404(slot_id, db)
    _assert_unbooked(slot_id, db)

    if body.starts_at is not None:
        slot.starts_at = body.starts_at
    if body.capacity is not None:
        slot.capacity = body.capacity

    db.commit()
    db.refresh(slot)

    booked_count = db.execute(
        select(func.count(Booking.id)).where(Booking.slot_id == slot.id)
    ).scalar_one()
    record(db, actor="admin", action="slot_update", detail=f"slot {slot.id} updated")
    return {
        "id": slot.id,
        "starts_at": slot.starts_at,
        "capacity": slot.capacity,
        "booked_count": booked_count,
        "is_open": booked_count < slot.capacity,
    }


@router.delete("/slots/{slot_id}")
def delete_slot(
    slot_id: int,
    db: Session = Depends(get_db),  # noqa: B008
    _: object = Depends(current_admin),  # noqa: B008
):
    slot = _get_slot_or_404(slot_id, db)
    _assert_unbooked(slot_id, db)

    db.delete(slot)
    db.commit()
    record(db, actor="admin", action="slot_delete", detail=f"slot {slot_id} deleted")
    return {"ok": True}
