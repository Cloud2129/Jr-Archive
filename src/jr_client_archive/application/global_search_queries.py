"""Cross-entity search bar (Fase 6): clients and documents in one query.

Two different matching strategies on purpose: the clients table is small
and every relevant column already indexed, so the substring ``LIKE`` in
``ClientRepository.search`` is plenty fast. The document corpus is the one
expected to grow large (filenames, classification, tags across every
client), which is what the SQLite FTS5 index in ``DocumentRepository.
search_fts`` is for.
"""

from __future__ import annotations

from jr_client_archive.db.base import Database
from jr_client_archive.domain.client import ClientRead
from jr_client_archive.domain.document import DocumentRead
from jr_client_archive.domain.search import GlobalSearchResult
from jr_client_archive.repositories.client_repository import ClientRepository
from jr_client_archive.repositories.document_repository import DocumentRepository

_MAX_CLIENT_RESULTS = 20
_MAX_DOCUMENT_RESULTS = 50


def global_search(database: Database, term: str) -> GlobalSearchResult:
    term = term.strip()
    if not term:
        return GlobalSearchResult()

    session = database.create_session()
    try:
        clients = ClientRepository(session).search(term)[:_MAX_CLIENT_RESULTS]
        documents = DocumentRepository(session).search_fts(term, limit=_MAX_DOCUMENT_RESULTS)
        return GlobalSearchResult(
            clients=[ClientRead.model_validate(client) for client in clients],
            documents=[DocumentRead.from_orm_document(document) for document in documents],
        )
    finally:
        session.close()
