"""Admin content library — upload / list / replace / delete assessment files.

POST   /api/admin/content              — upload a new file (multipart: file, label, category)
GET    /api/admin/content              — list all content files
PUT    /api/admin/content/{file_key}   — replace the file and/or update label/category
DELETE /api/admin/content/{file_key}   — delete the row and its on-disk file

Stored filenames and file_keys are server-generated (see app.content_storage),
so nothing the client sends is ever joined to a filesystem path.
"""

import mimetypes
import os

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import record
from app.config import get_settings
from app.content_storage import (
    ALLOWED_CATEGORIES,
    allocate_file_key,
    resolve_stored_path,
    stored_filename_for,
)
from app.db import get_db
from app.deps import current_admin
from app.models import ContentFile

router = APIRouter(prefix="/api/admin/content", tags=["admin-content"])

# 50 MB cap — generous for briefs/spreadsheets, bounded so a stray upload can't
# fill the content volume.
MAX_UPLOAD_BYTES = 50 * 1024 * 1024

_CHUNK = 1024 * 1024


def _serialize(row: ContentFile) -> dict:
    return {
        "file_key": row.file_key,
        "label": row.label,
        "category": row.category,
        "original_filename": row.original_filename,
        "media_type": row.media_type,
        "size_bytes": row.size_bytes,
        "uploaded_at": row.uploaded_at.isoformat() if row.uploaded_at else None,
    }


def _validate_label_category(label: str, category: str) -> tuple[str, str]:
    label = (label or "").strip()
    if not label:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="label must not be empty"
        )
    if category not in ALLOWED_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"category must be one of {sorted(ALLOWED_CATEGORIES)}",
        )
    return label, category


def _media_type_for(upload: UploadFile, original_filename: str) -> str:
    if upload.content_type and upload.content_type != "application/octet-stream":
        return upload.content_type
    guessed, _ = mimetypes.guess_type(original_filename)
    return guessed or "application/octet-stream"


async def _save_upload(upload: UploadFile, dest_path: str) -> int:
    """Stream *upload* to *dest_path*, enforcing MAX_UPLOAD_BYTES. Returns bytes written.

    On overflow the partial file is removed and a 413 is raised.
    """
    size = 0
    try:
        with open(dest_path, "wb") as f:
            while chunk := await upload.read(_CHUNK):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="file exceeds the 50 MB limit",
                    )
                f.write(chunk)
    except Exception:
        # Never leave a half-written file behind on any failure.
        if os.path.exists(dest_path):
            os.remove(dest_path)
        raise
    if size == 0:
        if os.path.exists(dest_path):
            os.remove(dest_path)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="file is empty"
        )
    return size


def _get_row_or_404(file_key: str, db: Session) -> ContentFile:
    row = db.execute(
        select(ContentFile).where(ContentFile.file_key == file_key)
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="content not found")
    return row


@router.get("")
def list_content_files(
    db: Session = Depends(get_db),  # noqa: B008
    _: object = Depends(current_admin),  # noqa: B008
):
    rows = (
        db.execute(
            select(ContentFile).order_by(ContentFile.sort_order, ContentFile.uploaded_at)
        )
        .scalars()
        .all()
    )
    return [_serialize(r) for r in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_content_file(
    file: UploadFile = File(...),  # noqa: B008
    label: str = Form(...),  # noqa: B008
    category: str = Form(...),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
    _: object = Depends(current_admin),  # noqa: B008
):
    label, category = _validate_label_category(label, category)
    original_filename = file.filename or "upload"

    settings = get_settings()
    os.makedirs(settings.content_dir, exist_ok=True)

    file_key = allocate_file_key()
    stored_filename = stored_filename_for(file_key, original_filename)
    dest_path = os.path.join(settings.content_dir, stored_filename)

    size = await _save_upload(file, dest_path)

    row = ContentFile(
        file_key=file_key,
        label=label,
        category=category,
        original_filename=original_filename,
        stored_filename=stored_filename,
        media_type=_media_type_for(file, original_filename),
        size_bytes=size,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    record(db, actor="admin", action="content_upload", detail=f"{file_key} ({label})")
    return _serialize(row)


@router.put("/{file_key}")
async def replace_content_file(
    file_key: str,
    file: UploadFile | None = File(None),  # noqa: B008
    label: str | None = Form(None),  # noqa: B008
    category: str | None = Form(None),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
    _: object = Depends(current_admin),  # noqa: B008
):
    """Update label/category and/or replace the underlying file.

    Any subset may be provided. If a new file is sent, the old on-disk file is
    removed after the new one is written.
    """
    row = _get_row_or_404(file_key, db)
    settings = get_settings()

    if label is not None:
        stripped = label.strip()
        if not stripped:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="label must not be empty",
            )
        row.label = stripped

    if category is not None:
        if category not in ALLOWED_CATEGORIES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"category must be one of {sorted(ALLOWED_CATEGORIES)}",
            )
        row.category = category

    if file is not None:
        os.makedirs(settings.content_dir, exist_ok=True)
        original_filename = file.filename or "upload"
        new_stored = stored_filename_for(allocate_file_key(), original_filename)
        new_path = os.path.join(settings.content_dir, new_stored)
        size = await _save_upload(file, new_path)

        old_stored = row.stored_filename
        row.stored_filename = new_stored
        row.original_filename = original_filename
        row.media_type = _media_type_for(file, original_filename)
        row.size_bytes = size

        # Remove the previous file (best-effort) now that the row points at the new one.
        old_path = resolve_stored_path(old_stored, settings.content_dir)
        if old_path is not None and old_stored != new_stored:
            try:
                old_path.unlink()
            except OSError:
                pass

    db.commit()
    db.refresh(row)
    record(db, actor="admin", action="content_update", detail=f"{file_key} ({row.label})")
    return _serialize(row)


@router.delete("/{file_key}")
def delete_content_file(
    file_key: str,
    db: Session = Depends(get_db),  # noqa: B008
    _: object = Depends(current_admin),  # noqa: B008
):
    row = _get_row_or_404(file_key, db)
    settings = get_settings()

    path = resolve_stored_path(row.stored_filename, settings.content_dir)
    db.delete(row)
    db.commit()
    if path is not None:
        try:
            path.unlink()
        except OSError:
            pass
    record(db, actor="admin", action="content_delete", detail=file_key)
    return {"ok": True}
