"""SQLAlchemy engine/session bootstrap.

A single :class:`Database` instance owns the engine and the session
factory for the whole process. It is constructed once in ``app.py`` (or in
a test fixture) and threaded through the repository layer via dependency
injection - nothing in this codebase imports a module-level global engine,
which keeps the test suite able to spin up as many isolated databases as it
wants.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from jr_client_archive.db.search_index import ensure_search_index


class Base(DeclarativeBase):
    """Shared declarative base for every ORM model in the application."""


class Database:
    """Owns the SQLAlchemy engine and produces sessions."""

    def __init__(self, database_path: Path, *, echo: bool = False) -> None:
        from sqlalchemy import create_engine

        self.database_path = database_path
        self.engine: Engine = create_engine(
            f"sqlite:///{database_path}",
            echo=echo,
            connect_args={"check_same_thread": False},
        )
        _enable_sqlite_pragmas(self.engine)
        self.session_factory: sessionmaker[Session] = sessionmaker(
            bind=self.engine, expire_on_commit=False
        )

    def create_session(self) -> Session:
        return self.session_factory()

    def create_all(self) -> None:
        """Create tables that don't exist yet.

        Used for first-run bootstrap and in tests. Schema *changes* to an
        existing database go through Alembic migrations, never through
        this method.
        """
        Base.metadata.create_all(self.engine)
        ensure_search_index(self.engine)

    def dispose(self) -> None:
        self.engine.dispose()


def _enable_sqlite_pragmas(engine: Engine) -> None:
    """WAL + foreign keys: required for concurrent reads and FK integrity.

    WAL mode in particular is what keeps the UI responsive while a
    background watchdog/import thread writes to the database.
    """

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()
