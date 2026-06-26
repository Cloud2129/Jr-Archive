"""Manual subfolder creation inside a client's archive.

Automatic detection of folders renamed/moved directly on disk (keeping the
database in lockstep via watchdog) is a later phase; this module only
covers the user explicitly clicking "new subfolder" from the dossier.
"""

from __future__ import annotations

from jr_client_archive.config.paths import get_app_paths
from jr_client_archive.db.base import Database
from jr_client_archive.db.models.folder import Folder
from jr_client_archive.domain.folder import FolderRead
from jr_client_archive.repositories.folder_repository import FolderRepository
from jr_client_archive.services.audit_service import AuditService
from jr_client_archive.services.filesystem_service import FilesystemService
from jr_client_archive.utils.text import normalize_token


def create_subfolder(
    database: Database, client_id: int, parent_folder_id: int, name: str, *, username: str
) -> FolderRead:
    session = database.create_session()
    try:
        folder_repo = FolderRepository(session)
        parent = folder_repo.get(parent_folder_id)
        if parent is None or parent.client_id != client_id:
            raise ValueError("Cartella padre non valida per questo cliente.")

        fs_service = FilesystemService(get_app_paths().archive_root)
        relative_path = fs_service.create_subfolder(parent.relative_path, name)

        folder = folder_repo.add(
            Folder(
                client_id=client_id,
                parent_id=parent.id,
                name=normalize_token(name),
                relative_path=relative_path,
                is_auto_generated=False,
            )
        )
        AuditService(session, username=username).record(
            "folder.created", entity_type="FOLDER", entity_id=folder.id,
            details=f"Sottocartella '{folder.name}' creata sotto {parent.relative_path}",
        )
        return FolderRead.model_validate(folder)
    finally:
        session.close()
