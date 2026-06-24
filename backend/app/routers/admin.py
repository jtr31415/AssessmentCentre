from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import record
from app.candidate_ids import allocate_candidate_id
from app.db import get_db
from app.deps import current_admin
from app.models import Candidate
from app.schemas import CreateCandidate
from app.security import generate_token

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _set_password_path(token: str) -> str:
    return f"/set-password?token={token}"


@router.post("/candidates", status_code=status.HTTP_201_CREATED)
def create_candidate(
    body: CreateCandidate,
    db: Session = Depends(get_db),  # noqa: B008
    _: object = Depends(current_admin),  # noqa: B008
):
    cid = allocate_candidate_id(db)
    token = generate_token()
    cand = Candidate(
        candidate_id=cid,
        first_name=body.first_name,
        status="invited",
        password_set_token=token,
        password_set_token_expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    db.add(cand)
    db.commit()
    record(db, actor="admin", action="candidate_create", detail=f"created {cid}")
    return {
        "candidate_id": cid,
        "first_name": cand.first_name,
        "status": cand.status,
        "set_password_path": _set_password_path(token),
    }


@router.get("/candidates")
def list_candidates(db: Session = Depends(get_db), _: object = Depends(current_admin)):  # noqa: B008
    rows = db.execute(select(Candidate).order_by(Candidate.candidate_id)).scalars().all()
    return [
        {
            "candidate_id": c.candidate_id,
            "first_name": c.first_name,
            "status": c.status,
            "has_password": c.password_hash is not None,
            "set_password_path": _set_password_path(c.password_set_token)
            if c.password_set_token
            else None,
        }
        for c in rows
    ]
