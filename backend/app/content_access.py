"""Content unlock gating.

``is_unlocked`` checks whether a candidate may currently access assessment
content.  ``require_unlocked`` is the FastAPI dependency that enforces this
gate on protected routes.
"""

from datetime import UTC, datetime

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import current_candidate
from app.models import Booking, Candidate


def is_unlocked(db: Session, candidate: Candidate) -> bool:
    """Return True iff the candidate is entitled to view content.

    All three conditions must hold:
    1. ``candidate.status == "active"``
    2. A ``Booking`` row exists for the candidate.
    3. ``datetime.now(UTC) >= booking.unlock_at``
    """
    if candidate.status != "active":
        return False

    booking = (
        db.query(Booking)
        .filter(Booking.candidate_id == candidate.id)
        .first()
    )
    if booking is None:
        return False

    return datetime.now(UTC) >= booking.unlock_at


def require_unlocked(
    cand: Candidate = Depends(current_candidate),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> Candidate:
    """FastAPI dependency — raises 403 if content is locked, else returns the candidate."""
    if not is_unlocked(db, cand):
        raise HTTPException(status_code=403, detail="content is locked")
    return cand
