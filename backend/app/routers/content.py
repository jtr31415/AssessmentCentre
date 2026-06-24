"""Gated content list and streamed file download.

GET  /api/content            — list available manifest entries (files that exist on disk)
GET  /api/content/{file_key} — stream the file to the candidate; writes audit + event
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from starlette.responses import FileResponse

from app.audit import record
from app.config import get_settings
from app.content_access import require_unlocked
from app.content_manifest import MANIFEST, get_entry, resolve_path
from app.db import get_db
from app.models import Candidate, DownloadEvent

router = APIRouter(prefix="/api/content", tags=["content"])


@router.get("")
def list_content(
    cand: Candidate = Depends(require_unlocked),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return manifest entries whose file exists on disk.  403 if locked (dep handles it)."""
    settings = get_settings()
    result = []
    for entry in MANIFEST:
        if resolve_path(entry["file_key"], settings.content_dir) is not None:
            result.append(
                {
                    "file_key": entry["file_key"],
                    "label": entry["label"],
                    "category": entry["category"],
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
    entry = get_entry(file_key)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="file not found")

    path = resolve_path(file_key, settings.content_dir)
    if path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="file not found")

    # Write download event and audit BEFORE returning (but AFTER confirming the file exists)
    db.add(DownloadEvent(candidate_id=cand.id, file_key=file_key))
    db.commit()
    record(db, actor=cand.candidate_id, action="file_download", detail=file_key)

    return FileResponse(
        path=str(path),
        filename=entry["filename"],
        media_type=entry["media_type"],
    )
