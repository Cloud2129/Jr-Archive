from __future__ import annotations

from sqlalchemy import select

from jr_client_archive.db.models.folder import Folder
from jr_client_archive.repositories.base import BaseRepository


class FolderRepository(BaseRepository[Folder]):
    model = Folder

    def list_by_client(self, client_id: int) -> list[Folder]:
        return list(
            self._session.scalars(
                select(Folder).where(Folder.client_id == client_id).order_by(Folder.name)
            )
        )

    def get_by_relative_path(self, relative_path: str) -> Folder | None:
        return self._session.scalar(select(Folder).where(Folder.relative_path == relative_path))

    def get_client_root_folder(self, client_id: int) -> Folder | None:
        return self._session.scalar(
            select(Folder).where(Folder.client_id == client_id, Folder.parent_id.is_(None))
        )
