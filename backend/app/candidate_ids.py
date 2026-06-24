from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Candidate


# Single-admin, sequential allocation by design — not safe under concurrent writers.
def allocate_candidate_id(db: Session) -> str:
    rows = db.execute(select(Candidate.candidate_id)).scalars().all()
    nums = [int(r.split("-")[1]) for r in rows if r.startswith("cand-")]
    nxt = (max(nums) + 1) if nums else 1
    return f"cand-{nxt:02d}"
