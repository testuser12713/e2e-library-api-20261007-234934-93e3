"""Database engine, session factory and schema bootstrap."""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    """Declarative base shared by every ORM model."""


def _connect_args(database_url: str) -> dict[str, object]:
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


_database_url = get_settings().database_url

engine = create_engine(_database_url, connect_args=_connect_args(_database_url))
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    """Create every table declared by the models."""

    from app import models  # noqa: F401  (import registers the tables on Base)

    Base.metadata.create_all(bind=engine)


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a database session."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
