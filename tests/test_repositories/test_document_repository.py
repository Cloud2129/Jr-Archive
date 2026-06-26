from __future__ import annotations

from datetime import datetime

from jr_client_archive.application.client_commands import CreateClientRequest, create_client
from jr_client_archive.application.folder_queries import list_folders_for_client
from jr_client_archive.db.models.document import Document
from jr_client_archive.domain.client import ClientCreate
from jr_client_archive.domain.enums import DocumentStatus
from jr_client_archive.repositories.document_repository import DocumentRepository, TagRepository


def _make_document(session, *, client_id, folder_id, relative_path, status=DocumentStatus.TO_VERIFY) -> Document:
    document = Document(
        client_id=client_id,
        folder_id=folder_id,
        original_filename="originale.pdf",
        stored_filename="originale.pdf",
        relative_path=relative_path,
        extension="pdf",
        size_bytes=10,
        checksum_sha256="abc123",
        uploaded_at=datetime.now(),
        uploaded_by="t",
        status=status,
    )
    DocumentRepository(session).add(document)
    return document


def test_list_by_folder_and_client(database, app_paths):
    client = create_client(
        database, CreateClientRequest(client=ClientCreate(first_name="Mario", last_name="Rossi")), username="t"
    )
    folder = list_folders_for_client(database, client.id)[0]

    session = database.create_session()
    try:
        _make_document(session, client_id=client.id, folder_id=folder.id, relative_path="a.pdf")
        _make_document(session, client_id=client.id, folder_id=folder.id, relative_path="b.pdf")
        session.flush()

        repo = DocumentRepository(session)
        assert len(repo.list_by_folder(folder.id)) == 2
        assert len(repo.list_by_client(client.id)) == 2
    finally:
        session.close()


def test_list_to_verify_filters_by_status(database, app_paths):
    client = create_client(
        database, CreateClientRequest(client=ClientCreate(first_name="Mario", last_name="Rossi")), username="t"
    )
    folder = list_folders_for_client(database, client.id)[0]

    session = database.create_session()
    try:
        _make_document(
            session, client_id=client.id, folder_id=folder.id, relative_path="a.pdf",
            status=DocumentStatus.TO_VERIFY,
        )
        _make_document(
            session, client_id=client.id, folder_id=folder.id, relative_path="b.pdf",
            status=DocumentStatus.CATALOGUED,
        )
        session.flush()

        to_verify = DocumentRepository(session).list_to_verify()
        assert [d.relative_path for d in to_verify] == ["a.pdf"]
    finally:
        session.close()


def test_get_by_relative_path(database, app_paths):
    client = create_client(
        database, CreateClientRequest(client=ClientCreate(first_name="Mario", last_name="Rossi")), username="t"
    )
    folder = list_folders_for_client(database, client.id)[0]

    session = database.create_session()
    try:
        _make_document(session, client_id=client.id, folder_id=folder.id, relative_path="a.pdf")
        session.flush()

        found = DocumentRepository(session).get_by_relative_path("a.pdf")
        assert found is not None
        assert DocumentRepository(session).get_by_relative_path("missing.pdf") is None
    finally:
        session.close()


def test_tag_repository_get_or_create_many_deduplicates(database, app_paths):
    session = database.create_session()
    try:
        repo = TagRepository(session)
        first = repo.get_or_create_many(["Urgente", "Fattura", "Urgente", "  "])
        assert [t.name for t in first] == ["Urgente", "Fattura", "Urgente"]

        second = repo.get_or_create_many(["Urgente"])
        assert second[0].id == first[0].id
        assert len(repo.list_all()) == 2
    finally:
        session.close()
