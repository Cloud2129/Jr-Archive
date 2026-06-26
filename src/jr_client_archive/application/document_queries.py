"""Read-only document use cases consumed by the UI.

Mirrors ``client_queries.py``: the UI only ever sees :class:`DocumentRead`
DTOs, never ORM rows or repositories. Each function owns its own
short-lived session.
"""

from __future__ import annotations

from jr_client_archive.db.base import Database
from jr_client_archive.domain.document import DocumentRead
from jr_client_archive.repositories.document_repository import DocumentRepository


def list_documents_for_folder(database: Database, folder_id: int) -> list[DocumentRead]:
    session = database.create_session()
    try:
        documents = DocumentRepository(session).list_by_folder(folder_id)
        return [DocumentRead.from_orm_document(document) for document in documents]
    finally:
        session.close()


def list_documents_for_client(database: Database, client_id: int) -> list[DocumentRead]:
    session = database.create_session()
    try:
        documents = DocumentRepository(session).list_by_client(client_id)
        return [DocumentRead.from_orm_document(document) for document in documents]
    finally:
        session.close()


def list_documents_to_verify(database: Database) -> list[DocumentRead]:
    session = database.create_session()
    try:
        documents = DocumentRepository(session).list_to_verify()
        return [DocumentRead.from_orm_document(document) for document in documents]
    finally:
        session.close()


def get_document(database: Database, document_id: int) -> DocumentRead | None:
    session = database.create_session()
    try:
        document = DocumentRepository(session).get(document_id)
        return DocumentRead.from_orm_document(document) if document else None
    finally:
        session.close()
