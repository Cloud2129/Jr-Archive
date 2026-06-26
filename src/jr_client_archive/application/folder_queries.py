from __future__ import annotations

from jr_client_archive.db.base import Database
from jr_client_archive.domain.folder import FolderRead
from jr_client_archive.repositories.folder_repository import FolderRepository


def list_folders_for_client(database: Database, client_id: int) -> list[FolderRead]:
    session = database.create_session()
    try:
        folders = FolderRepository(session).list_by_client(client_id)
        return [FolderRead.model_validate(folder) for folder in folders]
    finally:
        session.close()


def get_root_folder(database: Database, client_id: int) -> FolderRead | None:
    session = database.create_session()
    try:
        folder = FolderRepository(session).get_client_root_folder(client_id)
        return FolderRead.model_validate(folder) if folder else None
    finally:
        session.close()
