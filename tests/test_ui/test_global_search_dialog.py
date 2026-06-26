from __future__ import annotations

from PySide6.QtWidgets import QDialog

import jr_client_archive.ui.dialogs.global_search_dialog as global_search_dialog_module
from jr_client_archive.application.client_commands import CreateClientRequest, create_client
from jr_client_archive.application.document_commands import add_document
from jr_client_archive.application.folder_queries import list_folders_for_client
from jr_client_archive.domain.client import ClientCreate
from jr_client_archive.ui.dialogs.global_search_dialog import GlobalSearchDialog


def _create_client(database, first_name, last_name):
    return create_client(
        database,
        CreateClientRequest(client=ClientCreate(first_name=first_name, last_name=last_name)),
        username="t",
    )


def test_typing_a_term_populates_both_result_lists(qtbot, database, app_paths, tmp_path):
    client = _create_client(database, "Mario", "Rossi")
    folder = list_folders_for_client(database, client.id)[0]
    source = tmp_path / "fattura_rossi.pdf"
    source.write_bytes(b"contenuto")
    add_document(database, client.id, folder.id, source, username="t")

    dialog = GlobalSearchDialog(database, username="t")
    qtbot.addWidget(dialog)

    dialog._search_box.setText("rossi")

    assert dialog._client_results.count() == 1
    assert "Mario Rossi" in dialog._client_results.item(0).text()
    assert dialog._document_results.count() == 1
    assert "fattura_rossi.pdf" in dialog._document_results.item(0).text()


def test_empty_term_clears_results(qtbot, database, app_paths):
    _create_client(database, "Mario", "Rossi")
    dialog = GlobalSearchDialog(database, username="t")
    qtbot.addWidget(dialog)

    dialog._search_box.setText("rossi")
    dialog._search_box.setText("")

    assert dialog._client_results.count() == 0
    assert dialog._document_results.count() == 0


def test_no_match_shows_placeholders(qtbot, database, app_paths):
    dialog = GlobalSearchDialog(database, username="t")
    qtbot.addWidget(dialog)

    dialog._search_box.setText("inesistente")

    assert "Nessun cliente trovato" in dialog._client_results.item(0).text()
    assert "Nessun documento trovato" in dialog._document_results.item(0).text()


def test_double_click_client_result_opens_dossier(qtbot, database, app_paths, monkeypatch):
    _create_client(database, "Mario", "Rossi")
    dialog = GlobalSearchDialog(database, username="t")
    qtbot.addWidget(dialog)
    dialog._search_box.setText("rossi")

    opened = {}

    def _fake_exec(self):
        opened["client"] = self._client
        opened["select_document_id"] = self._select_document_id
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(global_search_dialog_module.ClientDossierDialog, "exec", _fake_exec)
    dialog._on_client_result_double_clicked(dialog._client_results.item(0))

    assert opened["client"].display_name == "Mario Rossi"
    assert opened["select_document_id"] is None


def test_double_click_document_result_opens_dossier_with_document_preselected(
    qtbot, database, app_paths, tmp_path, monkeypatch
):
    client = _create_client(database, "Mario", "Rossi")
    folder = list_folders_for_client(database, client.id)[0]
    source = tmp_path / "fattura_rossi.pdf"
    source.write_bytes(b"contenuto")
    document = add_document(database, client.id, folder.id, source, username="t")

    dialog = GlobalSearchDialog(database, username="t")
    qtbot.addWidget(dialog)
    dialog._search_box.setText("rossi")

    opened = {}

    def _fake_exec(self):
        opened["client"] = self._client
        opened["selected_document"] = self._selected_document()
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(global_search_dialog_module.ClientDossierDialog, "exec", _fake_exec)
    dialog._on_document_result_double_clicked(dialog._document_results.item(0))

    assert opened["client"].display_name == "Mario Rossi"
    assert opened["selected_document"] is not None
    assert opened["selected_document"].id == document.id
