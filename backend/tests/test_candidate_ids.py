from app.candidate_ids import allocate_candidate_id
from app.models import Candidate


def test_allocate_sequential(db_session):
    assert allocate_candidate_id(db_session) == "cand-01"
    db_session.add(Candidate(candidate_id="cand-01", first_name="A"))
    db_session.commit()
    assert allocate_candidate_id(db_session) == "cand-02"
