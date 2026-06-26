from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect

import jr_client_archive.db.models  # noqa: F401 - registers all ORM models
from jr_client_archive.db.base import Base

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_alembic_upgrade_head_creates_full_schema(tmp_path, monkeypatch):
    """Migrations are the real, production code path: ``create_all`` is a
    test-only shortcut, so we separately verify ``alembic upgrade head``
    produces every table the ORM models declare.
    """
    home = tmp_path / "app_home"
    monkeypatch.setenv("JR_CLIENT_ARCHIVE_HOME", str(home))

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=REPO_ROOT,
        env={**__import__("os").environ, "JR_CLIENT_ARCHIVE_HOME": str(home)},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    db_path = home / "database" / "archive.db"
    assert db_path.exists()

    engine = create_engine(f"sqlite:///{db_path}")
    actual_tables = set(inspect(engine).get_table_names())
    expected_tables = set(Base.metadata.tables) | {"alembic_version"}
    assert expected_tables <= actual_tables
