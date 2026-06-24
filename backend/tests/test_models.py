from app.models import Candidate


def test_candidate_roundtrip(db_session):
    c = Candidate(candidate_id="cand-01", first_name="Ada", status="invited")
    db_session.add(c)
    db_session.commit()
    fetched = db_session.query(Candidate).filter_by(candidate_id="cand-01").one()
    assert fetched.first_name == "Ada"
    assert fetched.password_hash is None
    assert fetched.status == "invited"
