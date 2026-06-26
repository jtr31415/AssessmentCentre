"""Gated content list and streamed file download (DB-backed).

GET  /api/content            — list available content files (rows whose file exists on disk)
GET  /api/content/{file_key} — stream the file to the candidate; writes audit + event

The set of downloadable files is the ``content_file`` table, managed by the
admin via /api/admin/content.  ``file_key`` is a server-generated opaque key,
so it is safe to take from the URL.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.responses import FileResponse

from app.audit import record
from app.config import get_settings
from app.content_access import require_unlocked
from app.content_storage import resolve_stored_path
from app.db import get_db
from app.models import Candidate, ContentFile, DownloadEvent

router = APIRouter(prefix="/api/content", tags=["content"])


@router.get("")
def list_content(
    cand: Candidate = Depends(require_unlocked),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return content files whose underlying file exists on disk. 403 if locked (dep handles it)."""
    settings = get_settings()
    rows = (
        db.execute(
            select(ContentFile).order_by(ContentFile.sort_order, ContentFile.uploaded_at)
        )
        .scalars()
        .all()
    )
    result = []
    for row in rows:
        if resolve_stored_path(row.stored_filename, settings.content_dir) is not None:
            result.append(
                {
                    "file_key": row.file_key,
                    "label": row.label,
                    "description": row.description,
                    "category": row.category,
                }
            )
    return result


@router.get("/{file_key}")
def download_content(
    file_key: str,
    cand: Candidate = Depends(require_unlocked),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    """Stream a file to the authenticated, unlocked candidate.

    - 403 if locked (handled by ``require_unlocked``).
    - 404 if file_key is unknown or the file does not exist on disk.
    - On success: write a DownloadEvent row + commit, then audit file_download.
    """
    settings = get_settings()
    row = db.execute(
        select(ContentFile).where(ContentFile.file_key == file_key)
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="file not found")

    path = resolve_stored_path(row.stored_filename, settings.content_dir)
    if path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="file not found")

    # Write download event and audit BEFORE returning (but AFTER confirming the file exists)
    db.add(DownloadEvent(candidate_id=cand.id, file_key=file_key))
    db.commit()
    record(db, actor=cand.candidate_id, action="file_download", detail=file_key)

    # Capture what FileResponse needs, then release the DB connection NOW. The
    # file is streamed after this function returns; without an explicit close the
    # yield-dependency would hold the connection for the whole download, so many
    # simultaneous/slow downloads could exhaust the pool.
    filename = row.original_filename
    media_type = row.media_type
    db.close()

    return FileResponse(
        path=str(path),
        filename=filename,
        media_type=media_type,
    )
