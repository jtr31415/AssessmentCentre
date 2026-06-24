from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import record
from app.db import get_db
from app.models import Admin, Candidate
from app.schemas import AdminLogin, CandidateLogin, SetPassword
from app.security import hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/admin/login")
def admin_login(body: AdminLogin, request: Request, db: Session = Depends(get_db)):  # noqa: B008
    admin = db.execute(select(Admin).filter_by(username=body.username)).scalar_one_or_none()
    if not admin or not verify_password(body.password, admin.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")
    request.session.update({"role": "admin", "admin_id": admin.id})
    record(db, actor="admin", action="login", detail=f"admin '{admin.username}' logged in")
    return {"role": "admin", "id": admin.id}


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return {"ok": True}


@router.get("/me")
def me(request: Request):
    role = request.session.get("role")
    if not role:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "not authenticated")
    return {
        "role": role,
        "id": request.session.get("admin_id") or request.session.get("candidate_pk"),
    }


@router.post("/candidate/set-password")
def candidate_set_password(body: SetPassword, db: Session = Depends(get_db)):  # noqa: B008
    cand = db.execute(
        select(Candidate).filter_by(password_set_token=body.token)
    ).scalar_one_or_none()
    expires = cand.password_set_token_expires_at if cand else None
    if not cand or expires is None or expires < datetime.now(UTC):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid or expired token")
    cand.password_hash = hash_password(body.password)
    cand.status = "active"
    cand.password_set_token = None
    cand.password_set_token_expires_at = None
    db.commit()
    record(db, actor=cand.candidate_id, action="password_set", detail="password set via token")
    return {"ok": True}


@router.post("/candidate/login")
def candidate_login(body: CandidateLogin, request: Request, db: Session = Depends(get_db)):  # noqa: B008
    cand = db.execute(
        select(Candidate).filter_by(candidate_id=body.candidate_id)
    ).scalar_one_or_none()
    if (
        not cand
        or cand.status != "active"
        or not cand.password_hash
        or not verify_password(body.password, cand.password_hash)
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")
    request.session.update({"role": "candidate", "candidate_pk": cand.id})
    record(db, actor=cand.candidate_id, action="login", detail="candidate logged in")
    return {"role": "candidate", "candidate_id": cand.candidate_id}
