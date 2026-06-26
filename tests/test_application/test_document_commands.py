from __future__ import annotations

import pytest

from jr_client_archive.application.client_commands import CreateClientRequest, create_client
from jr_client_archive.application.document_commands import add_document, catalog_document
from jr_client_archive.application.document_queries import (
    get_document,
    list_documents_for_client,
    list_documents_to_verify,
)
from jr_client_archive.application.folder_queries import list_folders_for_client
from jr_client_archive.domain.client import ClientCreate
from jr_client_archive.domain.document import DocumentCatalogUpdate
from jr_client_archive.domain.enums import DocumentStatus, HistoryEventType


def _create_client(database):
    return create_client(
        database, CreateClientRequest(client=ClientCreate(first_name="Mario", last_name="Rossi")), username="t"
    )


def _source_file(tmp_path, name="fattura_gennaio.pdf", content=b"contenuto originale"):
    source = tmp_path / "incoming" / name
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(content)
    return source


def test_add_document_copies_file_and_marks_to_verify(database, app_paths, tmp_path):
    client = _create_client(database)
    folder = list_folders_for_client(database, client.id)[0]
    source = _source_file(tmp_path)

    document = add_document(database, client.id, folder.id, source, username="t")

    assert document.status == DocumentStatus.TO_VERIFY
    assert document.original_filename == "fattura_gennaio.pdf"
    assert document.size_bytes == len(b"contenuto originale")
    assert document.checksum_sha256
    assert source.exists(), "il file originale non deve essere toccato"

    stored_path = app_paths.archive_root / document.relative_path
    assert stored_path.exists()
    assert stored_path.read_bytes() == b"contenuto originale"

    fetched = get_document(database, document.id)
    assert fetched.id == document.id


def test_add_document_rejects_folder_from_another_client(database, app_paths, tmp_path):
    client_a = _create_client(database)
    client_b = create_client(
        database, CreateClientRequest(client=ClientCreate(first_name="Luigi", last_name="Verdi")), username="t"
    )
    folder_b = list_folders_for_client(database, client_b.id)[0]
    source = _source_file(tmp_path)

    with pytest.raises(ValueError):
        add_document(database, client_a.id, folder_b.id, source, username="t")


def test_add_document_rejects_unknown_client(database, app_paths, tmp_path):
    client = _create_client(database)
    folder = list_folders_for_client(database, client.id)[0]
    source = _source_file(tmp_path)

    with pytest.raises(ValueError):
        add_document(database, 9999, folder.id, source, username="t")


def test_catalog_document_renames_and_marks_catalogued(database, app_paths, tmp_path):
    client = _create_client(database)
    folder = list_folders_for_client(database, client.id)[0]
    source = _source_file(tmp_path)
    document = add_document(database, client.id, folder.id, source, username="t")

    catalogued = catalog_document(
        database,
        document.id,
        DocumentCatalogUpdate(
            document_type="Fattura",
            category="Contabilita",
            description="Fattura di gennaio",
            document_date="2024-01-15",
            tags=["urgente", "2024"],
        ),
        username="t",
    )

    assert catalogued.status == DocumentStatus.CATALOGUED
    assert catalogued.document_type == "Fattura"
    assert set(catalogued.tags) == {"urgente", "2024"}
    assert catalogued.relative_path != document.relative_path
    assert (app_paths.archive_root / catalogued.relative_path).exists()
    assert not (app_paths.archive_root / document.relative_path).exists()


def test_catalog_document_records_history_entries(database, app_paths, tmp_path):
    client = _create_client(database)
    folder = list_folders_for_client(database, client.id)[0]
    source = _source_file(tmp_path)
    document = add_document(database, client.id, folder.id, source, username="t")

    catalog_document(
        database,
        document.id,
        DocumentCatalogUpdate(document_type="Fattura"),
        username="t",
    )

    session = database.create_session()
    try:
        from jr_client_archive.repositories.document_repository import DocumentRepository

        refreshed = DocumentRepository(session).get(document.id)
        event_types = [entry.event_type for entry in refreshed.history]
        assert event_types == [
            HistoryEventType.CREATED,
            HistoryEventType.RENAMED,
            HistoryEventType.CATALOGUED,
        ]
    finally:
        session.close()


def test_catalog_document_skips_rename_when_name_already_matches(database, app_paths, tmp_path):
    from jr_client_archive.config.settings import AppSettings, SettingsService

    session = database.create_session()
    try:
        SettingsService(session).save(AppSettings(document_naming_pattern="placeholder"))
    finally:
        session.close()

    client = _create_client(database)
    folder = list_folders_for_client(database, client.id)[0]
    # The naming pattern is sanitized to uppercase by render_document_stem,
    # so the source filename must already be uppercase to land on a no-op.
    source = _source_file(tmp_path, name="PLACEHOLDER.pdf")
    document = add_document(database, client.id, folder.id, source, username="t")

    catalogued = catalog_document(
        database, document.id, DocumentCatalogUpdate(document_type="Fattura"), username="t"
    )

    assert catalogued.relative_path == document.relative_path

    session = database.create_session()
    try:
        from jr_client_archive.repositories.document_repository import DocumentRepository

        refreshed = DocumentRepository(session).get(document.id)
        event_types = [entry.event_type for entry in refreshed.history]
        assert event_types == [HistoryEventType.CREATED, HistoryEventType.CATALOGUED]
    finally:
        session.close()


def test_catalog_document_rejects_unknown_document(database, app_paths):
    with pytest.raises(ValueError):
        catalog_document(database, 9999, DocumentCatalogUpdate(document_type="Fattura"), username="t")


def test_list_documents_to_verify_and_for_client(database, app_paths, tmp_path):
    client = _create_client(database)
    folder = list_folders_for_client(database, client.id)[0]
    first = add_document(database, client.id, folder.id, _source_file(tmp_path, "uno.pdf"), username="t")
    add_document(database, client.id, folder.id, _source_file(tmp_path, "due.pdf"), username="t")

    catalog_document(database, first.id, DocumentCatalogUpdate(document_type="Fattura"), username="t")

    assert len(list_documents_for_client(database, client.id)) == 2
    to_verify = list_documents_to_verify(database)
    assert len(to_verify) == 1
    assert to_verify[0].status == DocumentStatus.TO_VERIFY
