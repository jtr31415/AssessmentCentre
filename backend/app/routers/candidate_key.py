"""Candidate API-key reveal endpoint.

GET /api/me/api-key — gated by ``require_unlocked``.  Returns the plaintext
key decrypted from ``candidate.api_key_encrypted``.  The key is NEVER written
to any audit log — only the candidate_id is recorded.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.audit import record
from app.content_access import require_unlocked
from app.db import get_db
from app.models import Candidate
from app.security import decrypt_secret

router = APIRouter(prefix="/api/me", tags=["candidate-key"])

_KEY_USAGE_NOTE = (
    "This key is for the LLM features your application uses at runtime. "
    "It has a fixed budget; track your own spend from the token usage "
    "returned in API responses."
)


@router.get("/api-key")
def reveal_api_key(
    cand: Candidate = Depends(require_unlocked),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    if cand.api_key_encrypted is None:
        raise HTTPException(status_code=404, detail="no API key assigned yet")
    key = decrypt_secret(cand.api_key_encrypted)
    # Audit: log only the candidate_id — NEVER the key itself
    record(db, actor=cand.candidate_id, action="api_key_reveal", detail=cand.candidate_id)
    return {"api_key": key, "note": _KEY_USAGE_NOTE}
