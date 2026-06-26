"""Local backup & restore (Fase 7): a single zip snapshot of the whole
data root (database + client document tree), restorable without losing
whatever is currently on disk.

Two constraints from the product spec drive the design:

- "Mai cancellare automaticamente file": a restore necessarily replaces
  today's database and documents with an older snapshot, but nothing is
  ever deleted to do it. Whatever is currently on disk - the database file
  (plus its WAL/SHM sidecars) and the entire client document tree - is
  *moved*, never removed, into a dedicated safety folder under
  ``backups_dir`` before the chosen backup is extracted into place.
- Everything stays local: a backup is just a zip file under the app's own
  ``backups_dir``; the user is free to copy it to a USB stick/NAS by hand.

The database file backed up/restored is always ``database.database_path``
(the live ``Database`` instance's own file), not a path derived from
``AppPaths`` - the two coincide in the running application but are
deliberately decoupled here, the same way the rest of the app is, so the
service has no assumption about where the caller's database actually
lives.
"""

from __future__ import annotations

import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from jr_client_archive.config.paths import AppPaths
from jr_client_archive.db.base import Database
from jr_client_archive.domain.backup import BackupInfo, RestoreResult

_BACKUP_PREFIX = "backup_"
_SAFETY_PREFIX = "pre_ripristino_"
_DB_ARCNAME = "database.sqlite3"
_TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S_%f"


class BackupService:
    def __init__(self, paths: AppPaths) -> None:
        self._paths = paths

    def create_backup(self, database: Database) -> BackupInfo:
        self._checkpoint_wal(database)

        backup_path = self._paths.backups_dir / f"{_BACKUP_PREFIX}{self._timestamp()}.zip"
        archive_root = self._paths.archive_root
        with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.write(database.database_path, arcname=_DB_ARCNAME)
            if archive_root.exists():
                for file_path in archive_root.rglob("*"):
                    if file_path.is_file():
                        arcname = f"{archive_root.name}/{file_path.relative_to(archive_root)}"
                        archive.write(file_path, arcname=arcname)

        return BackupInfo(
            path=backup_path, created_at=datetime.now(), size_bytes=backup_path.stat().st_size
        )

    def list_backups(self) -> list[BackupInfo]:
        backups = []
        for backup_path in sorted(self._paths.backups_dir.glob(f"{_BACKUP_PREFIX}*.zip"), reverse=True):
            stat = backup_path.stat()
            backups.append(
                BackupInfo(
                    path=backup_path,
                    created_at=datetime.fromtimestamp(stat.st_mtime),
                    size_bytes=stat.st_size,
                )
            )
        return backups

    def restore_backup(self, database: Database, backup_path: Path) -> RestoreResult:
        archive_root = self._paths.archive_root
        archive_prefix = f"{archive_root.name}/"

        with zipfile.ZipFile(backup_path) as archive:
            names = archive.namelist()
            if _DB_ARCNAME not in names:
                raise ValueError("Il file di backup non contiene un database valido.")

            database.dispose()

            safety_dir = self._paths.backups_dir / f"{_SAFETY_PREFIX}{self._timestamp()}"
            safety_dir.mkdir(parents=True)
            self._move_db_files_aside(database.database_path, safety_dir)
            if archive_root.exists():
                shutil.move(str(archive_root), str(safety_dir / archive_root.name))

            database.database_path.parent.mkdir(parents=True, exist_ok=True)
            self._extract_member(archive, _DB_ARCNAME, database.database_path)

            for name in names:
                if name == _DB_ARCNAME or not name.startswith(archive_prefix) or name.endswith("/"):
                    continue
                self._extract_member(archive, name, self._paths.root / name)

        self._paths.ensure_directories()
        return RestoreResult(safety_backup_dir=safety_dir)

    def _extract_member(self, archive: zipfile.ZipFile, name: str, target_path: Path) -> None:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(name) as source, open(target_path, "wb") as target:
            shutil.copyfileobj(source, target)

    def _move_db_files_aside(self, db_path: Path, safety_dir: Path) -> None:
        for suffix in ("", "-wal", "-shm"):
            candidate = db_path.with_name(db_path.name + suffix)
            if candidate.exists():
                shutil.move(str(candidate), str(safety_dir / candidate.name))

    def _checkpoint_wal(self, database: Database) -> None:
        with database.engine.connect() as connection:
            connection.exec_driver_sql("PRAGMA wal_checkpoint(FULL)")

    def _timestamp(self) -> str:
        return datetime.now().strftime(_TIMESTAMP_FORMAT)
