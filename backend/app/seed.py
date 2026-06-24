from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Admin, Config
from app.security import hash_password

_DEFAULT_CONFIG = {
    "retention_date": None,
    "qa_sla_text": "Questions are answered by a person, usually within 1 working day.",
}


def seed_admin_and_config(db: Session) -> None:
    s = get_settings()
    if not db.execute(select(Admin).filter_by(username=s.initial_admin_username)).first():
        db.add(Admin(
            username=s.initial_admin_username,
            password_hash=hash_password(s.initial_admin_password),
        ))
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
