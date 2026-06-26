from __future__ import annotations

from PySide6.QtWidgets import QDialog

from jr_client_archive.application.client_commands import CreateClientRequest, create_client
from jr_client_archive.application.client_matching_queries import match_clients_for_filename
from jr_client_archive.domain.client import ClientCreate
from jr_client_archive.ui.dialogs.document_match_dialog import DocumentMatchDialog


def _create_client(database, **kwargs):
    return create_client(database, CreateClientRequest(client=ClientCreate(**kwargs)), username="t")


def test_dialog_preselects_top_suggestion(qtbot, database, app_paths):
    client = _create_client(database, first_name="Mario", last_name="Rossi", fiscal_code="RSSMRA80A01H501Z")
    candidates = match_clients_for_filename(database, "RSSMRA80A01H501Z_fattura.pdf")

    dialog = DocumentMatchDialog(database, "RSSMRA80A01H501Z_fattura.pdf", candidates)
    qtbot.addWidget(dialog)

    assert dialog.selected_client().id == client.id


def test_dialog_has_no_preselection_when_no_candidates(qtbot, database, app_paths):
    _create_client(database, first_name="Mario", last_name="Rossi")

    dialog = DocumentMatchDialog(database, "documento_ignoto.pdf", [])
    qtbot.addWidget(dialog)

    assert dialog.selected_client() is None
    assert dialog._suggestions_list.count() == 1
    assert "Nessuna corrispondenza" in dialog._suggestions_list.item(0).text()


def test_dialog_allows_manual_selection_from_all_clients(qtbot, database, app_paths):
    _create_client(database, first_name="Mario", last_name="Rossi", fiscal_code="RSSMRA80A01H501Z")
    other = _create_client(database, first_name="Luigi", last_name="Verdi")
    candidates = match_clients_for_filename(database, "RSSMRA80A01H501Z_fattura.pdf")

    dialog = DocumentMatchDialog(database, "RSSMRA80A01H501Z_fattura.pdf", candidates)
    qtbot.addWidget(dialog)

    manual_items = [dialog._all_clients_list.item(i) for i in range(dialog._all_clients_list.count())]
    manual_item = next(item for item in manual_items if item.text() == other.display_name)
    dialog._on_manual_clicked(manual_item)

    assert dialog.selected_client().id == other.id


def test_dialog_rejects_accept_without_selection(qtbot, database, app_paths, monkeypatch):
    _create_client(database, first_name="Mario", last_name="Rossi")

    dialog = DocumentMatchDialog(database, "documento_ignoto.pdf", [])
    qtbot.addWidget(dialog)

    from PySide6.QtWidgets import QMessageBox

    warned = {}
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: warned.setdefault("shown", True)))

    dialog._on_accept()

    assert warned.get("shown") is True
    assert dialog.result() != QDialog.DialogCode.Accepted
