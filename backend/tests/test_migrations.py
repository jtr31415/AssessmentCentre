import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Candidate


def test_candidate_id_unique(db_session):
    db_session.add(Candidate(candidate_id="cand-01", first_name="A"))
    db_session.commit()
    db_session.add(Candidate(candidate_id="cand-01", first_name="B"))
    with pytest.raises(IntegrityError):
        db_session.commit()
