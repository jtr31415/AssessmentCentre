from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import record
from app.candidate_ids import allocate_candidate_id
from app.db import get_db
from app.deps import current_admin
from app.models import Candidate
from app.schemas import ApiKeyPaste, CreateCandidate
from app.security import encrypt_secret, generate_token

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


@router.put("/candidates/{candidate_id}/api-key")
def set_api_key(
    candidate_id: str,
    body: ApiKeyPaste,
    db: Session = Depends(get_db),  # noqa: B008
    _: object = Depends(current_admin),  # noqa: B008
):
    cand = db.execute(
        select(Candidate).where(Candidate.candidate_id == candidate_id)
    ).scalar_one_or_none()
    if cand is None:
        raise HTTPException(status_code=404, detail="candidate not found")
    cand.api_key_encrypted = encrypt_secret(body.api_key)
    db.commit()
    # Audit: log only the candidate_id — NEVER the key itself
    record(db, actor="admin", action="api_key_set", detail=candidate_id)
    return {"ok": True}


@router.delete("/candidates/{candidate_id}/api-key")
def clear_api_key(
    candidate_id: str,
    db: Session = Depends(get_db),  # noqa: B008
    _: object = Depends(current_admin),  # noqa: B008
):
    cand = db.execute(
        select(Candidate).where(Candidate.candidate_id == candidate_id)
    ).scalar_one_or_none()
    if cand is None:
        raise HTTPException(status_code=404, detail="candidate not found")
    cand.api_key_encrypted = None
    db.commit()
    # Audit: log only the candidate_id — NEVER the key itself
    record(db, actor="admin", action="api_key_clear", detail=candidate_id)
    return {"ok": True}
