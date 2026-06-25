import zoneinfo
from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import record
from app.candidate_ids import allocate_candidate_id
from app.db import get_db
from app.deps import current_admin
from app.models import (
    AuditLog,
    Booking,
    Candidate,
    Config,
    ContentFile,
    DownloadEvent,
    Question,
    Slot,
)
from app.schemas import ApiKeyPaste, ConfigSet, CreateCandidate, PurgeRequest
from app.security import decrypt_secret, encrypt_secret, generate_token

_ALLOWED_CONFIG_KEYS = {
    "prep_window_days",
    "retention_date",
    "qa_sla_text",
    "display_timezone",
    "assessment_format",
    "assessment_duration",
    "assessment_location",
    "api_docs_url",
    "api_tier",
}

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

    # Map candidate pk -> their booking (slot start + id + unlock), if any.
    booking_rows = db.execute(
        select(Booking.candidate_id, Booking.slot_id, Booking.unlock_at, Slot.starts_at)
        .join(Slot, Booking.slot_id == Slot.id)
    ).all()
    booking_map = {b.candidate_id: b for b in booking_rows}

    result = []
    for c in rows:
        bk = booking_map.get(c.id)
        # Last 4 chars of the API key, for verification only (never the full key).
        api_key_last4 = None
        if c.api_key_encrypted:
            try:
                api_key_last4 = decrypt_secret(c.api_key_encrypted)[-4:]
            except Exception:
                api_key_last4 = None
        result.append(
            {
                "candidate_id": c.candidate_id,
                "first_name": c.first_name,
                "status": c.status,
                "has_password": c.password_hash is not None,
                "api_key_last4": api_key_last4,
                "set_password_path": _set_password_path(c.password_set_token)
                if c.password_set_token
                else None,
                "booked_slot_id": bk.slot_id if bk else None,
                "booked_slot_at": bk.starts_at.isoformat() if bk else None,
                "unlock_at": bk.unlock_at.isoformat() if bk else None,
            }
        )
    return result


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


def _issue_set_password_token(cand: Candidate) -> str:
    """Mint a fresh 24-hour set-password token on *cand* and return the raw token."""
    token = generate_token()
    cand.password_set_token = token
    cand.password_set_token_expires_at = datetime.now(UTC) + timedelta(hours=24)
    return token


def _get_candidate_or_404(candidate_id: str, db: Session) -> Candidate:
    cand = db.execute(
        select(Candidate).where(Candidate.candidate_id == candidate_id)
    ).scalar_one_or_none()
    if cand is None:
        raise HTTPException(status_code=404, detail="candidate not found")
    return cand


@router.post("/candidates/{candidate_id}/reset-password")
def reset_password(
    candidate_id: str,
    db: Session = Depends(get_db),  # noqa: B008
    _: object = Depends(current_admin),  # noqa: B008
):
    cand = _get_candidate_or_404(candidate_id, db)
    token = _issue_set_password_token(cand)
    db.commit()
    record(db, actor="admin", action="password_reset", detail=candidate_id)
    return {"set_password_path": _set_password_path(token)}


@router.post("/candidates/{candidate_id}/reissue-invite")
def reissue_invite(
    candidate_id: str,
    db: Session = Depends(get_db),  # noqa: B008
    _: object = Depends(current_admin),  # noqa: B008
):
    cand = _get_candidate_or_404(candidate_id, db)
    token = _issue_set_password_token(cand)
    db.commit()
    record(db, actor="admin", action="invite_reissue", detail=candidate_id)
    return {"set_password_path": _set_password_path(token)}


@router.post("/candidates/{candidate_id}/disable")
def disable_candidate(
    candidate_id: str,
    db: Session = Depends(get_db),  # noqa: B008
    _: object = Depends(current_admin),  # noqa: B008
):
    cand = _get_candidate_or_404(candidate_id, db)
    cand.status = "disabled"
    db.commit()
    record(db, actor="admin", action="account_disable", detail=candidate_id)
    return {"status": cand.status}


@router.post("/candidates/{candidate_id}/enable")
def enable_candidate(
    candidate_id: str,
    db: Session = Depends(get_db),  # noqa: B008
    _: object = Depends(current_admin),  # noqa: B008
):
    cand = _get_candidate_or_404(candidate_id, db)
    cand.status = "active" if cand.password_hash else "invited"
    db.commit()
    record(db, actor="admin", action="account_enable", detail=candidate_id)
    return {"status": cand.status}


@router.delete("/candidates/{candidate_id}")
def delete_candidate(
    candidate_id: str,
    body: PurgeRequest,
    db: Session = Depends(get_db),  # noqa: B008
    _: object = Depends(current_admin),  # noqa: B008
):
    """Permanently delete a single candidate and all their data.

    Requires the ``confirm`` field to exactly match the candidate's ID, to guard
    against accidental deletion. Removes their bookings, questions, download
    events, and candidate-attributable audit rows (admin audit is kept).
    """
    cand = _get_candidate_or_404(candidate_id, db)
    if body.confirm != candidate_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="confirmation must exactly match the candidate ID",
        )

    n_downloads = db.query(DownloadEvent).filter_by(candidate_id=cand.id).count()
    n_questions = db.query(Question).filter_by(candidate_id=cand.id).count()
    n_bookings = db.query(Booking).filter_by(candidate_id=cand.id).count()

    # FK-safe order: children before the candidate row; then their audit rows.
    db.query(DownloadEvent).filter_by(candidate_id=cand.id).delete()
    db.query(Question).filter_by(candidate_id=cand.id).delete()
    db.query(Booking).filter_by(candidate_id=cand.id).delete()
    db.query(AuditLog).filter(AuditLog.actor == candidate_id).delete(synchronize_session=False)
    db.delete(cand)
    db.commit()

    record(
        db,
        actor="admin",
        action="candidate_delete",
        detail=(
            f"deleted {candidate_id} ({n_bookings} bookings, {n_questions} questions, "
            f"{n_downloads} downloads)"
        ),
    )
    return {
        "deleted": {
            "candidate_id": candidate_id,
            "bookings": n_bookings,
            "questions": n_questions,
            "download_events": n_downloads,
        }
    }


@router.get("/activity")
def get_activity(
    db: Session = Depends(get_db),  # noqa: B008
    _: object = Depends(current_admin),  # noqa: B008
):
    """Return one monitoring row per candidate, ordered by candidate_id."""
    # Download columns come from the current content library (ordered for stable display).
    content_keys = (
        db.execute(
            select(ContentFile.file_key).order_by(
                ContentFile.sort_order, ContentFile.uploaded_at
            )
        )
        .scalars()
        .all()
    )

    candidates = (
        db.execute(select(Candidate).order_by(Candidate.candidate_id)).scalars().all()
    )

    rows = []
    for cand in candidates:
        # Booking + slot
        booking = db.execute(
            select(Booking).where(Booking.candidate_id == cand.id)
        ).scalar_one_or_none()

        if booking:
            slot = db.get(Slot, booking.slot_id)
            slot_starts_at = slot.starts_at.isoformat() if slot else None
            unlock_at = booking.unlock_at.isoformat()
        else:
            slot_starts_at = None
            unlock_at = None

        # has_logged_in
        login_exists = db.execute(
            select(AuditLog).where(
                AuditLog.actor == cand.candidate_id,
                AuditLog.action == "login",
            )
        ).first()

        # key_revealed
        reveal_exists = db.execute(
            select(AuditLog).where(
                AuditLog.actor == cand.candidate_id,
                AuditLog.action == "api_key_reveal",
            )
        ).first()

        # downloads — latest downloaded_at per file_key
        download_rows = db.execute(
            select(DownloadEvent.file_key, func.max(DownloadEvent.downloaded_at).label("latest"))
            .where(DownloadEvent.candidate_id == cand.id)
            .group_by(DownloadEvent.file_key)
        ).all()
        download_map = {row.file_key: row.latest for row in download_rows}
        downloads = {
            key: (download_map[key].isoformat() if key in download_map else None)
            for key in content_keys
        }

        # question_count
        question_count = db.execute(
            select(func.count(Question.id)).where(Question.candidate_id == cand.id)
        ).scalar()

        rows.append({
            "candidate_id": cand.candidate_id,
            "first_name": cand.first_name,
            "status": cand.status,
            "has_booking": booking is not None,
            "slot_starts_at": slot_starts_at,
            "unlock_at": unlock_at,
            "has_logged_in": login_exists is not None,
            "downloads": downloads,
            "key_revealed": reveal_exists is not None,
            "question_count": question_count,
            "nda_accepted_at": cand.nda_accepted_at.isoformat() if cand.nda_accepted_at else None,
            "nda_declined_at": cand.nda_declined_at.isoformat() if cand.nda_declined_at else None,
        })

    return rows


@router.post("/purge")
def purge_all_candidate_data(
    body: PurgeRequest,
    db: Session = Depends(get_db),  # noqa: B008
    _: object = Depends(current_admin),  # noqa: B008
):
    """Right to erasure: delete all candidate data in FK-safe order, in one transaction.

    Keeps: admin accounts, config table, admin-actor audit rows.
    Requires exact confirmation phrase to prevent accidental data loss.
    """
    if body.confirm != "PURGE ALL CANDIDATE DATA":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="confirmation phrase did not match",
        )

    # Capture counts BEFORE deleting (within the same transaction)
    n_download_events = db.query(DownloadEvent).count()
    n_questions = db.query(Question).count()
    n_bookings = db.query(Booking).count()
    n_candidates = db.query(Candidate).count()
    n_audit_rows = db.query(AuditLog).filter(AuditLog.actor != "admin").count()

    # Delete in FK-safe order: children before parents; candidate-attributable audit rows last
    db.query(DownloadEvent).delete()
    db.query(Question).delete()
    db.query(Booking).delete()
    db.query(Candidate).delete()
    db.query(AuditLog).filter(AuditLog.actor != "admin").delete(synchronize_session=False)

    db.commit()

    # Audit the purge itself (after commit so this row survives)
    detail = (
        f"purged {n_candidates} candidates, {n_bookings} bookings, "
        f"{n_questions} questions, {n_download_events} download_events, "
        f"{n_audit_rows} audit_rows"
    )
    record(db, actor="admin", action="data_purge", detail=detail)

    return {
        "deleted": {
            "candidates": n_candidates,
            "bookings": n_bookings,
            "questions": n_questions,
            "download_events": n_download_events,
            "audit_rows": n_audit_rows,
        }
    }


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


@router.get("/notifications")
def admin_notifications(
    db: Session = Depends(get_db),  # noqa: B008
    _: object = Depends(current_admin),  # noqa: B008
):
    """Lightweight badge poll: how many candidate questions are still unanswered."""
    pending = db.execute(
        select(func.count(Question.id)).where(Question.answer.is_(None))
    ).scalar()
    return {"unanswered_questions": pending or 0}


@router.get("/config")
def get_config(
    db: Session = Depends(get_db),  # noqa: B008
    _: object = Depends(current_admin),  # noqa: B008
):
    """Return all config rows as a flat dict {key: value}."""
    rows = db.execute(select(Config)).scalars().all()
    return {row.key: row.value for row in rows}


def _validate_config_value(key: str, value: str | None) -> str | None:
    """Validate value for the given key; return the stored value or raise HTTPException 422."""
    if key == "prep_window_days":
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="prep_window_days must be a positive integer",
            ) from None
        if parsed <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="prep_window_days must be a positive integer",
            )
        return value

    if key == "retention_date":
        if value is None or value == "":
            return None
        try:
            date.fromisoformat(value)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="retention_date must be an ISO date (YYYY-MM-DD) or empty to clear",
            ) from None
        return value

    if key == "display_timezone":
        if not value:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="display_timezone must not be empty",
            )
        try:
            zoneinfo.ZoneInfo(value)
        except (zoneinfo.ZoneInfoNotFoundError, KeyError):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"display_timezone '{value}' is not a valid timezone",
            ) from None
        return value

    # qa_sla_text: any non-None string
    return value


@router.put("/config/{key}")
def set_config(
    key: str,
    body: ConfigSet,
    db: Session = Depends(get_db),  # noqa: B008
    _: object = Depends(current_admin),  # noqa: B008
):
    """Upsert a config row for the given key after validation."""
    if key not in _ALLOWED_CONFIG_KEYS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="unknown config key",
        )

    stored_value = _validate_config_value(key, body.value)

    row = db.execute(select(Config).where(Config.key == key)).scalar_one_or_none()
    if row is None:
        db.add(Config(key=key, value=stored_value))
    else:
        row.value = stored_value
    db.commit()

    record(db, actor="admin", action="config_update", detail=key)

    return {"key": key, "value": stored_value}
