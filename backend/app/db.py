from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


# pool_size 10 + max_overflow 20 = up to 30 connections (Postgres default
# max_connections is 100). Ample headroom for the whole cohort hitting at once.
engine = create_engine(
    get_settings().database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
