import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Candidate

# Random, non-sequential 4-digit IDs (cand-1000 .. cand-9999) so a candidate's
# own ID never reveals how many candidates exist. CSPRNG → also unguessable.
_LOW = 1000
_HIGH = 9999
_MAX_ATTEMPTS = 10000


def allocate_candidate_id(db: Session) -> str:
    """Return a fresh unique candidate id of the form ``cand-XXXX`` (4 random digits)."""
    existing = set(db.execute(select(Candidate.candidate_id)).scalars().all())
    for _ in range(_MAX_ATTEMPTS):
        cid = f"cand-{secrets.randbelow(_HIGH - _LOW + 1) + _LOW}"
        if cid not in existing:
            return cid
    # Effectively unreachable for any realistic candidate count (9000 slots).
    raise RuntimeError("could not allocate a unique candidate id")
