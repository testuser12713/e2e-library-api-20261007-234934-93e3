"""Shared pytest fixtures backed by a fresh in-memory SQLite database."""

import secrets
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def engine() -> Iterator[Engine]:
    """A fresh in-memory SQLite database with the full schema created."""

    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    try:
        yield test_engine
    finally:
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()


@pytest.fixture()
def db_session(engine: Engine) -> Iterator[Session]:
    """A session on the same test database the client uses."""

    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = testing_session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(engine: Engine) -> Iterator[TestClient]:
    """TestClient with ``get_db`` overridden to the test database.

    The context-manager form runs the application lifespan, which exercises the
    real schema-creation path.
    """

    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db() -> Iterator[Session]:
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers(monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[str, str]]:
    """Headers carrying a per-run generated API key (never a literal)."""

    key = secrets.token_hex(32)
    monkeypatch.setenv("LIBRARY_API_KEY", key)
    get_settings.cache_clear()
    try:
        yield {"X-API-Key": key}
    finally:
        get_settings.cache_clear()
