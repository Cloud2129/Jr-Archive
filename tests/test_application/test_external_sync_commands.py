from __future__ import annotations

from jr_client_archive.application.client_commands import CreateClientRequest, create_client
from jr_client_archive.application.document_commands import add_document
from jr_client_archive.application.external_sync_commands import (
    EXTERNAL_SYNC_ACTOR,
    reconcile_external_move,
)
from jr_client_archive.application.folder_commands import create_subfolder
from jr_client_archive.application.folder_queries import list_folders_for_client
from jr_client_archive.db.models.audit import AuditLogEntry
from jr_client_archive.db.models.client import Client
from jr_client_archive.domain.client import ClientCreate
from jr_client_archive.domain.enums import HistoryEventType
from jr_client_archive.repositories.document_repository import DocumentRepository
from jr_client_archive.repositories.folder_repository import FolderRepository


def _create_client(database):
    return create_client(
        database, CreateClientRequest(client=ClientCreate(first_name="Mario", last_name="Rossi")), username="t"
    )


def _source_file(tmp_path, name="fattura.pdf", content=b"contenuto"):
    source = tmp_path / "incoming" / name
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(content)
    return source


def test_reconcile_document_rename_in_same_folder(database, app_paths, tmp_path):
    client = _create_client(database)
    folder = list_folders_for_client(database, client.id)[0]
    document = add_document(database, client.id, folder.id, _source_file(tmp_path), username="t")

    old_path = document.relative_path
    new_path = str(old_path).rsplit("/", 1)[0] + "/rinominato.pdf"

    reconciled = reconcile_external_move(database, old_path, new_path, is_directory=False)
    assert reconciled is True

    session = database.create_session()
    try:
        refreshed = DocumentRepository(session).get(document.id)
        assert refreshed.relative_path == new_path
        assert refreshed.stored_filename == "rinominato.pdf"
        last_entry = refreshed.history[-1]
        assert last_entry.event_type == HistoryEventType.RENAMED
        assert last_entry.old_value == old_path
        assert last_entry.new_value == new_path
        assert last_entry.performed_by == EXTERNAL_SYNC_ACTOR
    finally:
        session.close()

    session = database.create_session()
    try:
        entries = session.query(AuditLogEntry).filter_by(action="document.external_sync").all()
        assert len(entries) == 1
        assert entries[0].username == EXTERNAL_SYNC_ACTOR
    finally:
        session.close()


def test_reconcile_document_moved_to_different_folder(database, app_paths, tmp_path):
    client = _create_client(database)
    root_folder = list_folders_for_client(database, client.id)[0]
    document = add_document(database, client.id, root_folder.id, _source_file(tmp_path), username="t")

    old_path = document.relative_path
    new_path = f"{root_folder.relative_path}/altra_cartella/{document.stored_filename}"

    reconciled = reconcile_external_move(database, old_path, new_path, is_directory=False)
    assert reconciled is True

    session = database.create_session()
    try:
        refreshed = DocumentRepository(session).get(document.id)
        assert refreshed.relative_path == new_path
        assert refreshed.history[-1].event_type == HistoryEventType.MOVED
    finally:
        session.close()


def test_reconcile_document_untracked_path_returns_false(database, app_paths):
    reconciled = reconcile_external_move(
        database, "qualunque/percorso.pdf", "qualunque/nuovo.pdf", is_directory=False
    )
    assert reconciled is False


def test_reconcile_folder_rename_cascades_to_documents_and_subfolders(database, app_paths, tmp_path):
    client = _create_client(database)
    root_folder = list_folders_for_client(database, client.id)[0]
    subfolder = create_subfolder(database, client.id, root_folder.id, "Contratti", username="t")
    document = add_document(database, client.id, subfolder.id, _source_file(tmp_path), username="t")

    old_root_path = root_folder.relative_path
    new_root_path = f"{old_root_path}_RINOMINATA"

    reconciled = reconcile_external_move(database, old_root_path, new_root_path, is_directory=True)
    assert reconciled is True

    session = database.create_session()
    try:
        refreshed_root = FolderRepository(session).get(root_folder.id)
        assert refreshed_root.relative_path == new_root_path

        refreshed_subfolder = FolderRepository(session).get(subfolder.id)
        assert refreshed_subfolder.relative_path == subfolder.relative_path.replace(
            old_root_path, new_root_path, 1
        )

        refreshed_document = DocumentRepository(session).get(document.id)
        assert refreshed_document.relative_path == document.relative_path.replace(
            old_root_path, new_root_path, 1
        )
        assert refreshed_document.history[-1].event_type == HistoryEventType.MOVED

        refreshed_client = session.get(Client, client.id)
        assert refreshed_client.folder_relative_path == new_root_path
    finally:
        session.close()


def test_reconcile_folder_untracked_path_returns_false(database, app_paths):
    reconciled = reconcile_external_move(
        database, "qualunque/cartella", "qualunque/nuova_cartella", is_directory=True
    )
    assert reconciled is False
