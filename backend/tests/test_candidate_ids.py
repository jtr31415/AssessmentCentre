import re

from app.candidate_ids import allocate_candidate_id
from app.models import Candidate

_PATTERN = re.compile(r"^cand-\d{4}$")


def test_allocated_id_is_4_random_digits(db_session):
    cid = allocate_candidate_id(db_session)
    assert _PATTERN.match(cid), cid
    n = int(cid.split("-")[1])
    assert 1000 <= n <= 9999


def test_allocations_are_unique(db_session):
    """Allocate several IDs, persisting each; all must be distinct and never collide."""
    seen: set[str] = set()
    for _ in range(20):
        cid = allocate_candidate_id(db_session)
        assert cid not in seen, f"duplicate id {cid}"
        seen.add(cid)
        db_session.add(Candidate(candidate_id=cid, first_name="X"))
        db_session.commit()
    assert len(seen) == 20


def test_stays_4_digits_even_with_high_existing_id(db_session):
    """A high existing id must not push allocation to 5 digits (old max+1 bug)."""
    db_session.add(Candidate(candidate_id="cand-9999", first_name="A"))
    db_session.commit()
    cid = allocate_candidate_id(db_session)
    assert _PATTERN.match(cid), cid  # never cand-10000
    assert cid != "cand-9999"
