"""Filesystem layout of the application.

All "where does X live on disk" decisions are centralized here so the rest
of the codebase never hardcodes a path. The root location can be overridden
with the ``JR_CLIENT_ARCHIVE_HOME`` environment variable, which is what makes
the test suite (and a future "portable mode") possible without touching the
real user profile.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_APP_DIR_NAME = "JR Client Archive"


def _default_data_root() -> Path:
    """Resolve the OS-appropriate per-user data directory.

    Windows -> %APPDATA%\\JR Client Archive
    macOS   -> ~/Library/Application Support/JR Client Archive
    Linux   -> $XDG_DATA_HOME/JR Client Archive (or ~/.local/share/...)
    """
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / _APP_DIR_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / _APP_DIR_NAME
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / _APP_DIR_NAME


@dataclass(frozen=True)
class AppPaths:
    """Immutable description of every directory/file the app touches."""

    root: Path

    @property
    def database_dir(self) -> Path:
        return self.root / "database"

    @property
    def database_file(self) -> Path:
        return self.database_dir / "archive.db"

    @property
    def archive_root(self) -> Path:
        """Root folder containing every client's physical folder/document tree."""
        return self.root / "Archivio Clienti"

    @property
    def logs_dir(self) -> Path:
        return self.root / "logs"

    @property
    def backups_dir(self) -> Path:
        return self.root / "backups"

    @property
    def temp_dir(self) -> Path:
        return self.root / "temp"

    def ensure_directories(self) -> None:
        for directory in (
            self.database_dir,
            self.archive_root,
            self.logs_dir,
            self.backups_dir,
            self.temp_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_app_paths() -> AppPaths:
    """Return the process-wide :class:`AppPaths`, created on first access."""
    override = os.environ.get("JR_CLIENT_ARCHIVE_HOME")
    root = Path(override).expanduser() if override else _default_data_root()
    paths = AppPaths(root=root)
    paths.ensure_directories()
    return paths
