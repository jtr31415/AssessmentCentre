from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Admin, Candidate


def current_admin(request: Request, db: Session = Depends(get_db)) -> Admin:  # noqa: B008
    if request.session.get("role") != "admin":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "admin auth required")
    admin = db.get(Admin, request.session.get("admin_id"))
    if not admin:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "admin auth required")
    return admin


def current_candidate(request: Request, db: Session = Depends(get_db)) -> Candidate:  # noqa: B008
    if request.session.get("role") != "candidate":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "candidate auth required")
    cand = db.get(Candidate, request.session.get("candidate_pk"))
    if not cand:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "candidate auth required")
    # Re-check status on every request: a candidate disabled AFTER login must be
    # cut off immediately, not just blocked from new logins (in-flight session).
    if cand.status != "active":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "account is not active")
    return cand


def require_nda(cand: Candidate = Depends(current_candidate)) -> Candidate:  # noqa: B008
    """Gate participation on NDA acceptance.

    The candidate may browse the NDA page and read their own profile without
    accepting, but cannot take part in the exercise (book, access data, ask
    questions, reveal key) until they accept. 403 otherwise.
    """
    if cand.nda_accepted_at is None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "NDA acceptance required to take part"
        )
    return cand
