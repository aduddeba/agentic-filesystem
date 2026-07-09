"""Shared fixtures for tests that need a real Postgres + pgvector instance.

pgvector's `Vector` column type and its distance operators (`cosine_distance`,
etc.) are Postgres-only, so indexing/semantic-search tests can't use the
in-memory SQLite fixture that `test_api_files.py` uses for plain CRUD. These
fixtures self-provision a dedicated `agentic_filesystem_test` database
(separate from the real dev database) and skip gracefully if Postgres isn't
reachable -- the same pattern `test_search.py` uses for missing ripgrep.
"""

import psycopg2
import pytest
from fastapi.testclient import TestClient
from psycopg2 import errors as pg_errors
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

import app.main as main_module
from app import config as config_module
from app.database import Base, get_db
from app.main import app

MAINTENANCE_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/postgres"
TEST_DATABASE_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/agentic_filesystem_test"


def _ensure_test_database() -> None:
    conn = psycopg2.connect(MAINTENANCE_DATABASE_URL)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("CREATE DATABASE agentic_filesystem_test")
    except pg_errors.DuplicateDatabase:
        pass
    finally:
        conn.close()


@pytest.fixture
def pg_engine():
    try:
        _ensure_test_database()
        engine = create_engine(TEST_DATABASE_URL)
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
    except (psycopg2.OperationalError, OperationalError):
        pytest.skip(f"Postgres with pgvector not reachable at {TEST_DATABASE_URL}")

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture
def pg_session(pg_engine):
    SessionLocal = sessionmaker(bind=pg_engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def pg_client(tmp_path, monkeypatch, pg_engine):
    monkeypatch.setattr(config_module.settings, "storage_root", str(tmp_path))

    TestingSessionLocal = sessionmaker(bind=pg_engine, autoflush=False, autocommit=False)

    # main.py's lifespan touches the module-level `engine`/`SessionLocal` directly
    # (not through the `get_db` dependency), so it must be redirected too.
    monkeypatch.setattr(main_module, "engine", pg_engine)
    monkeypatch.setattr(main_module, "SessionLocal", TestingSessionLocal)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
