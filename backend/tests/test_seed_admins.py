"""Tests for multi-admin seeding (extra_admins)."""

from sqlalchemy import select

from app.config import get_settings
from app.models import Admin
from app.seed import _parse_extra_admins, seed_admin_and_config


def test_parse_extra_admins_handles_format_and_junk():
    parsed = _parse_extra_admins("Alice:pw1, Bob:pw2 ,,bad-entry,:nopass,name:")
    assert parsed == [("Alice", "pw1"), ("Bob", "pw2")]


def test_seeds_extra_admins_idempotently(db_session, monkeypatch):
    monkeypatch.setattr(get_settings(), "extra_admins", "JTrodler:secret-a,JKuhlin:secret-b")

    seed_admin_and_config(db_session)
    seed_admin_and_config(db_session)  # second call must not duplicate

    usernames = set(db_session.execute(select(Admin.username)).scalars().all())
    assert {"JTrodler", "JKuhlin"}.issubset(usernames)

    # Idempotent: exactly one of each
    for name in ("JTrodler", "JKuhlin"):
        rows = db_session.execute(select(Admin).filter_by(username=name)).scalars().all()
        assert len(rows) == 1


def test_existing_admin_password_not_overwritten(db_session, monkeypatch):
    monkeypatch.setattr(get_settings(), "extra_admins", "JTrodler:first-pw")
    seed_admin_and_config(db_session)
    original_hash = db_session.execute(
        select(Admin).filter_by(username="JTrodler")
    ).scalar_one().password_hash

    # Re-seed with a different password for the same username → must NOT change.
    monkeypatch.setattr(get_settings(), "extra_admins", "JTrodler:second-pw")
    seed_admin_and_config(db_session)
    new_hash = db_session.execute(
        select(Admin).filter_by(username="JTrodler")
    ).scalar_one().password_hash
    assert original_hash == new_hash
