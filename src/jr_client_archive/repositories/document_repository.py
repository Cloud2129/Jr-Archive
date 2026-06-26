from __future__ import annotations

from sqlalchemy import select

from jr_client_archive.db.models.document import Document, Tag
from jr_client_archive.domain.enums import DocumentStatus
from jr_client_archive.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    model = Document

    def list_by_folder(self, folder_id: int) -> list[Document]:
        return list(
            self._session.scalars(
                select(Document).where(Document.folder_id == folder_id).order_by(Document.uploaded_at.desc())
            )
        )

    def list_by_client(self, client_id: int) -> list[Document]:
        return list(
            self._session.scalars(
                select(Document).where(Document.client_id == client_id).order_by(Document.uploaded_at.desc())
            )
        )

    def list_to_verify(self) -> list[Document]:
        return list(
            self._session.scalars(
                select(Document)
                .where(Document.status == DocumentStatus.TO_VERIFY)
                .order_by(Document.uploaded_at.desc())
            )
        )

    def get_by_relative_path(self, relative_path: str) -> Document | None:
        return self._session.scalar(select(Document).where(Document.relative_path == relative_path))


class TagRepository(BaseRepository[Tag]):
    model = Tag

    def get_or_create_many(self, names: list[str]) -> list[Tag]:
        """Resolves a list of tag names to ``Tag`` rows, creating any that
        don't exist yet. Order and case are preserved as typed; only exact
        duplicates collapse to the same row.
        """
        tags = []
        for raw_name in names:
            name = raw_name.strip()
            if not name:
                continue
            tag = self._session.scalar(select(Tag).where(Tag.name == name))
            if tag is None:
                tag = Tag(name=name)
                self._session.add(tag)
                self._session.flush()
            tags.append(tag)
        return tags
