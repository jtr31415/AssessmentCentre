from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Admin, Config
from app.security import hash_password

_DEFAULT_CONFIG = {
    "retention_date": None,
    "qa_sla_text": "Questions are answered by a person, usually within 1 working day.",
    # Assessment session details shown to candidates (admin-editable in Settings).
    "assessment_format": "In person",
    "assessment_duration": "",
    "assessment_location": "",
}


def _parse_extra_admins(raw: str) -> list[tuple[str, str]]:
    """Parse "user1:pass1,user2:pass2" into [(user, pass), ...], skipping malformed entries."""
    out: list[tuple[str, str]] = []
    for chunk in (raw or "").split(","):
        chunk = chunk.strip()
        if not chunk or ":" not in chunk:
            continue
        username, password = chunk.split(":", 1)
        username, password = username.strip(), password.strip()
        if username and password:
            out.append((username, password))
    return out


def _seed_admin(db: Session, username: str, password: str) -> None:
    """Create the admin if no account with that username exists (never overwrites)."""
    if not db.execute(select(Admin).filter_by(username=username)).first():
        db.add(Admin(username=username, password_hash=hash_password(password)))


def seed_admin_and_config(db: Session) -> None:
    s = get_settings()
    _seed_admin(db, s.initial_admin_username, s.initial_admin_password)
    for username, password in _parse_extra_admins(s.extra_admins):
        _seed_admin(db, username, password)
    existing = set(db.execute(select(Config.key)).scalars().all())
    seeds = {
        "prep_window_days": str(s.prep_window_days),
        "display_timezone": s.display_timezone,
        **_DEFAULT_CONFIG,
    }
    for key, value in seeds.items():
        if key not in existing:
            db.add(Config(key=key, value=value))
    db.commit()
