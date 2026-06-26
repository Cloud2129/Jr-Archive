"""Use cases for Fase 7 (backup & restore): thin orchestration over
``BackupService`` plus an audit trail entry for every backup created or
restored.
"""

from __future__ import annotations

from pathlib import Path

from jr_client_archive.config.paths import get_app_paths
from jr_client_archive.db.base import Database
from jr_client_archive.domain.backup import BackupInfo, RestoreResult
from jr_client_archive.services.audit_service import AuditService
from jr_client_archive.services.backup_service import BackupService


def create_backup(database: Database, *, username: str) -> BackupInfo:
    info = BackupService(get_app_paths()).create_backup(database)
    _record_audit(database, username=username, action="backup.created", details=f"Backup creato: {info.path.name}")
    return info


def list_backups() -> list[BackupInfo]:
    return BackupService(get_app_paths()).list_backups()


def restore_backup(database: Database, backup_path: Path, *, username: str) -> RestoreResult:
    result = BackupService(get_app_paths()).restore_backup(database, backup_path)
    _record_audit(
        database,
        username=username,
        action="backup.restored",
        details=(
            f"Ripristino da '{backup_path.name}'. "
            f"Stato precedente conservato in '{result.safety_backup_dir.name}'."
        ),
    )
    return result


def _record_audit(database: Database, *, username: str, action: str, details: str) -> None:
    session = database.create_session()
    try:
        AuditService(session, username=username).record(action, entity_type="BACKUP", details=details)
    finally:
        session.close()
