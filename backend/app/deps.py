from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Admin, Candidate


def current_admin(request: Request, db: Session = Depends(get_db)) -> Admin:
    if request.session.get("role") != "admin":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "admin auth required")
    admin = db.get(Admin, request.session.get("admin_id"))
    if not admin:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "admin auth required")
    return admin


def current_candidate(request: Request, db: Session = Depends(get_db)) -> Candidate:
    if request.session.get("role") != "candidate":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "candidate auth required")
    cand = db.get(Candidate, request.session.get("candidate_pk"))
    if not cand:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "candidate auth required")
    return cand
