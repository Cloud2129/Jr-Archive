from __future__ import annotations

from PySide6.QtWidgets import QDialog

import jr_client_archive.ui.main_window as main_window_module
from jr_client_archive.application.client_commands import CreateClientRequest, create_client
from jr_client_archive.application.document_queries import list_documents_for_client
from jr_client_archive.config.paths import AppPaths
from jr_client_archive.domain.client import ClientCreate
from jr_client_archive.ui.main_window import MainWindow


def _create_client(database, **kwargs):
    return create_client(database, CreateClientRequest(client=ClientCreate(**kwargs)), username="t")


def test_to_verify_dashboard_shows_placeholder_when_empty(qtbot, database, app_paths, tmp_path):
    paths = AppPaths(root=tmp_path)
    window = MainWindow(database=database, paths=paths)
    qtbot.addWidget(window)

    assert window._to_verify_list.count() == 1
    assert "Nessun documento" in window._to_verify_list.item(0).text()


def test_handle_dropped_file_imports_document_into_matched_client(
    qtbot, database, app_paths, monkeypatch, tmp_path
):
    client = _create_client(database, first_name="Mario", last_name="Rossi")
    paths = AppPaths(root=tmp_path)
    window = MainWindow(database=database, paths=paths)
    qtbot.addWidget(window)

    source = tmp_path / "rossi_mario_fattura.pdf"
    source.write_bytes(b"contenuto")

    def _fake_exec(self):
        self._selected_client = client
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(main_window_module.DocumentMatchDialog, "exec", _fake_exec)

    window._handle_dropped_file(source)

    documents = list_documents_for_client(database, client.id)
    assert len(documents) == 1
    assert documents[0].original_filename == "rossi_mario_fattura.pdf"
    assert window._to_verify_list.count() == 1
    assert "Mario Rossi" in window._to_verify_list.item(0).text()


def test_handle_dropped_file_does_nothing_when_dialog_cancelled(
    qtbot, database, app_paths, monkeypatch, tmp_path
):
    _create_client(database, first_name="Mario", last_name="Rossi")
    paths = AppPaths(root=tmp_path)
    window = MainWindow(database=database, paths=paths)
    qtbot.addWidget(window)

    source = tmp_path / "documento.pdf"
    source.write_bytes(b"contenuto")

    monkeypatch.setattr(
        main_window_module.DocumentMatchDialog, "exec", lambda self: QDialog.DialogCode.Rejected
    )

    window._handle_dropped_file(source)

    assert window._to_verify_list.count() == 1
    assert "Nessun documento" in window._to_verify_list.item(0).text()


def test_to_verify_double_click_opens_dossier_and_reloads(
    qtbot, database, app_paths, monkeypatch, tmp_path
):
    client = _create_client(database, first_name="Mario", last_name="Rossi")
    paths = AppPaths(root=tmp_path)
    window = MainWindow(database=database, paths=paths)
    qtbot.addWidget(window)

    source = tmp_path / "rossi_mario_fattura.pdf"
    source.write_bytes(b"contenuto")

    def _fake_match_exec(self):
        self._selected_client = client
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(main_window_module.DocumentMatchDialog, "exec", _fake_match_exec)
    window._handle_dropped_file(source)

    opened = {}

    def _fake_dossier_exec(self):
        opened["client"] = self._client
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(main_window_module.ClientDossierDialog, "exec", _fake_dossier_exec)
    window._on_to_verify_double_clicked(window._to_verify_list.item(0))

    assert opened["client"].display_name == "Mario Rossi"
