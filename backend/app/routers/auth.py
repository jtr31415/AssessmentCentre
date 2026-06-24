from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import record
from app.db import get_db
from app.models import Admin
from app.schemas import AdminLogin
from app.security import verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/admin/login")
def admin_login(body: AdminLogin, request: Request, db: Session = Depends(get_db)):
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
    return {"role": role, "id": request.session.get("admin_id") or request.session.get("candidate_pk")}
