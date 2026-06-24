from app.audit import record
from app.models import AuditLog


def test_record_writes_row(db_session):
    record(db_session, actor="admin", action="login", detail="ok")
    row = db_session.query(AuditLog).one()
    assert row.actor == "admin"
    assert row.action == "login"
    assert row.detail == "ok"
    assert row.created_at is not None
