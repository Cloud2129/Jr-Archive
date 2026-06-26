from __future__ import annotations

from pathlib import Path

from jr_client_archive.application.client_commands import CreateClientRequest, create_client
from jr_client_archive.application.document_commands import add_document, catalog_document
from jr_client_archive.application.folder_queries import list_folders_for_client
from jr_client_archive.domain.client import ClientCreate
from jr_client_archive.domain.document import DocumentCatalogUpdate
from jr_client_archive.repositories.document_repository import DocumentRepository


def _upload(database, client_id, folder_id, tmp_path, filename, content=b"contenuto"):
    source = tmp_path / filename
    source.write_bytes(content)
    return add_document(database, client_id, folder_id, source, username="t")


def test_search_fts_matches_filename(database, app_paths, tmp_path):
    client = create_client(
        database, CreateClientRequest(client=ClientCreate(first_name="Mario", last_name="Rossi")), username="t"
    )
    folder = list_folders_for_client(database, client.id)[0]
    _upload(database, client.id, folder.id, tmp_path, "fattura_gennaio.pdf")
    _upload(database, client.id, folder.id, tmp_path, "preventivo.pdf")

    session = database.create_session()
    try:
        results = DocumentRepository(session).search_fts("fattura")
        assert [d.original_filename for d in results] == ["fattura_gennaio.pdf"]
    finally:
        session.close()


def test_search_fts_matches_tags_and_classification(database, app_paths, tmp_path):
    client = create_client(
        database, CreateClientRequest(client=ClientCreate(first_name="Mario", last_name="Rossi")), username="t"
    )
    folder = list_folders_for_client(database, client.id)[0]
    document = _upload(database, client.id, folder.id, tmp_path, "doc.pdf")
    catalog_document(
        database,
        document.id,
        DocumentCatalogUpdate(document_type="Fattura", category="Contabilita", tags=["urgente", "2024"]),
        username="t",
    )

    session = database.create_session()
    try:
        repo = DocumentRepository(session)
        assert len(repo.search_fts("urgente")) == 1
        assert len(repo.search_fts("Contabilita")) == 1
        assert len(repo.search_fts("Fattura")) == 1
    finally:
        session.close()


def test_search_fts_reflects_tag_removal(database, app_paths, tmp_path):
    client = create_client(
        database, CreateClientRequest(client=ClientCreate(first_name="Mario", last_name="Rossi")), username="t"
    )
    folder = list_folders_for_client(database, client.id)[0]
    document = _upload(database, client.id, folder.id, tmp_path, "doc.pdf")
    catalog_document(
        database, document.id, DocumentCatalogUpdate(document_type="Fattura", tags=["urgente"]), username="t"
    )
    catalog_document(
        database, document.id, DocumentCatalogUpdate(document_type="Fattura", tags=["archiviato"]), username="t"
    )

    session = database.create_session()
    try:
        repo = DocumentRepository(session)
        assert repo.search_fts("urgente") == []
        assert len(repo.search_fts("archiviato")) == 1
    finally:
        session.close()


def test_search_fts_empty_term_returns_empty(database, app_paths):
    session = database.create_session()
    try:
        assert DocumentRepository(session).search_fts("   ") == []
    finally:
        session.close()


def test_search_fts_special_characters_do_not_raise(database, app_paths, tmp_path):
    client = create_client(
        database, CreateClientRequest(client=ClientCreate(first_name="Mario", last_name="Rossi")), username="t"
    )
    folder = list_folders_for_client(database, client.id)[0]
    _upload(database, client.id, folder.id, tmp_path, "fattura-2024.pdf")

    session = database.create_session()
    try:
        results = DocumentRepository(session).search_fts('fattura-2024:test "quoted" (parens)')
        assert isinstance(results, list)
    finally:
        session.close()
