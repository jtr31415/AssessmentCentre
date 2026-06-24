"""Config-table helpers.

Reads key/value rows from the `config` table (see models.Config).
Returns the typed value or the supplied default when the key is absent or NULL.
"""

from sqlalchemy.orm import Session

from app.models import Config


def get_config_str(db: Session, key: str, default: str) -> str:
    """Return the config value for *key* as a str, or *default* if absent/NULL."""
    row = db.get(Config, key)
    if row is None or row.value is None:
        return default
    return row.value


def get_config_int(db: Session, key: str, default: int) -> int:
    """Return the config value for *key* as an int, or *default* if absent/NULL."""
    row = db.get(Config, key)
    if row is None or row.value is None:
        return default
    return int(row.value)
