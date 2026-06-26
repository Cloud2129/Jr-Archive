from __future__ import annotations

from sqlalchemy import select, text

from jr_client_archive.db.models.document import Document, Tag
from jr_client_archive.domain.enums import DocumentStatus
from jr_client_archive.repositories.base import BaseRepository


def _fts_match_query(term: str) -> str:
    """Builds a safe FTS5 MATCH expression from free-typed user input.

    Every token is quoted as an FTS5 string literal (embedded ``"``
    doubled per FTS5 escaping rules) and suffixed with ``*`` for prefix
    matching - this sidesteps FTS5's own query syntax (colons, hyphens,
    parentheses...) entirely, so a search term like "fattura-2024" can
    never raise a MATCH syntax error.
    """
    tokens = [token.replace('"', '""') for token in term.strip().split() if token]
    return " ".join(f'"{token}"*' for token in tokens)


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

    def search_fts(self, term: str, *, limit: int = 50) -> list[Document]:
        """Full-text search over filename/classification/tags via the
        ``document_search_index`` FTS5 table (see ``db.search_index``).

        Results come back ranked by FTS5's ``bm25()`` relevance, most
        relevant first - the in-clause re-fetch below would otherwise lose
        that order, so it's restored explicitly against the matched ids.
        """
        match_query = _fts_match_query(term)
        if not match_query:
            return []
        rows = self._session.execute(
            text(
                "SELECT document_id FROM document_search_index "
                "WHERE document_search_index MATCH :match_query "
                "ORDER BY bm25(document_search_index) LIMIT :limit"
            ),
            {"match_query": match_query, "limit": limit},
        ).all()
        ordered_ids = [row[0] for row in rows]
        if not ordered_ids:
            return []
        documents_by_id = {
            document.id: document
            for document in self._session.scalars(select(Document).where(Document.id.in_(ordered_ids)))
        }
        return [documents_by_id[document_id] for document_id in ordered_ids if document_id in documents_by_id]


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
