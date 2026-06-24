from sqlalchemy.orm import Session

from app.models import AuditLog


def record(db: Session, actor: str, action: str, detail: str | None = None) -> None:
    """Single choke-point for audit writes. Never pass secret material as detail."""
    db.add(AuditLog(actor=actor, action=action, detail=detail))
    db.commit()
