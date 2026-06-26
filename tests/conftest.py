from __future__ import annotations

import os

import pytest

import jr_client_archive.db.models  # noqa: F401 - registers all ORM models
from jr_client_archive.db.base import Database


@pytest.fixture
def database(tmp_path) -> Database:
    """A fresh, in-memory-equivalent SQLite database per test.

    Uses ``create_all`` rather than running Alembic migrations: that keeps
    the unit test suite fast and independent of migration history, while
    a dedicated migration test (see ``test_db/test_migrations.py``)
    verifies ``alembic upgrade head`` produces an equivalent schema.
    """
    db = Database(tmp_path / "test_archive.db")
    db.create_all()
    yield db
    db.dispose()


@pytest.fixture
def app_paths(tmp_path, monkeypatch):
    from jr_client_archive.config.paths import get_app_paths

    monkeypatch.setenv("JR_CLIENT_ARCHIVE_HOME", str(tmp_path / "app_home"))
    get_app_paths.cache_clear()
    paths = get_app_paths()
    yield paths
    get_app_paths.cache_clear()
