from __future__ import annotations

from jr_client_archive.application.client_commands import CreateClientRequest, create_client
from jr_client_archive.application.document_commands import add_document
from jr_client_archive.application.document_queries import get_document
from jr_client_archive.application.folder_queries import list_folders_for_client
from jr_client_archive.domain.client import ClientCreate
from jr_client_archive.ui.main_window import MainWindow


def _create_client(database, **kwargs):
    return create_client(database, CreateClientRequest(client=ClientCreate(**kwargs)), username="t")


def test_on_external_move_reconciles_document_and_reloads_dashboard(qtbot, database, app_paths, tmp_path):
    client = _create_client(database, first_name="Mario", last_name="Rossi")
    folder = list_folders_for_client(database, client.id)[0]
    source = tmp_path / "fattura.pdf"
    source.write_bytes(b"contenuto")
    document = add_document(database, client.id, folder.id, source, username="t")

    window = MainWindow(database=database, paths=app_paths)
    qtbot.addWidget(window)

    old_path = document.relative_path
    new_path = str(old_path).rsplit("/", 1)[0] + "/rinominato.pdf"
    window._on_external_move(old_path, new_path, False)

    refreshed = get_document(database, document.id)
    assert refreshed.relative_path == new_path
    assert window._to_verify_list.count() == 1
    assert "Mario Rossi" in window._to_verify_list.item(0).text()


def test_on_external_move_swallows_reconciliation_errors(qtbot, database, app_paths, monkeypatch, tmp_path):
    import jr_client_archive.ui.main_window as main_window_module

    window = MainWindow(database=database, paths=app_paths)
    qtbot.addWidget(window)

    def _raise(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(main_window_module, "reconcile_external_move", _raise)

    window._on_external_move("vecchio.pdf", "nuovo.pdf", False)  # non deve propagare l'eccezione


def test_start_external_sync_detects_real_rename_on_disk(qtbot, database, app_paths, tmp_path):
    client = _create_client(database, first_name="Mario", last_name="Rossi")
    folder = list_folders_for_client(database, client.id)[0]
    source = tmp_path / "fattura.pdf"
    source.write_bytes(b"contenuto")
    document = add_document(database, client.id, folder.id, source, username="t")

    window = MainWindow(database=database, paths=app_paths)
    qtbot.addWidget(window)
    window.start_external_sync()
    try:
        stored_path = app_paths.archive_root / document.relative_path
        new_stored_path = stored_path.parent / "rinominato_esternamente.pdf"
        stored_path.rename(new_stored_path)

        def _reconciled() -> bool:
            refreshed = get_document(database, document.id)
            return refreshed.relative_path.endswith("rinominato_esternamente.pdf")

        qtbot.waitUntil(_reconciled, timeout=5000)
    finally:
        window.close()

    refreshed = get_document(database, document.id)
    assert refreshed.relative_path.endswith("rinominato_esternamente.pdf")


def test_close_event_stops_the_watch_service(qtbot, database, app_paths):
    window = MainWindow(database=database, paths=app_paths)
    qtbot.addWidget(window)
    window.start_external_sync()

    service = window._folder_watch_service
    assert service is not None
    assert service._observer.is_alive()

    window.close()

    assert not service._observer.is_alive()
