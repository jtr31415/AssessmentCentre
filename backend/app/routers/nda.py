"""NDA acceptance at first login.

POST /api/me/nda/accept   — candidate accepts the data-handling terms
POST /api/me/nda/decline  — candidate declines (cannot take part)

The two timestamps on the candidate are mutually exclusive: accepting clears
the decline and vice-versa, so "currently accepted" == ``nda_accepted_at`` is
set.  The full history of accept/decline actions is kept in the audit log.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.audit import record
from app.db import get_db
from app.deps import current_candidate
from app.models import Candidate

me_router = APIRouter(prefix="/api/me/nda", tags=["nda"])


@me_router.post("/accept")
def accept_nda(
    cand: Candidate = Depends(current_candidate),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    now = datetime.now(UTC)
    cand.nda_accepted_at = now
    cand.nda_declined_at = None
    db.commit()
    record(db, actor=cand.candidate_id, action="nda_accept", detail=cand.candidate_id)
    return {"nda_accepted": True, "nda_accepted_at": now.isoformat()}


@me_router.post("/decline")
def decline_nda(
    cand: Candidate = Depends(current_candidate),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    now = datetime.now(UTC)
    cand.nda_declined_at = now
    cand.nda_accepted_at = None
    db.commit()
    record(db, actor=cand.candidate_id, action="nda_decline", detail=cand.candidate_id)
    return {"nda_declined": True, "nda_declined_at": now.isoformat()}
