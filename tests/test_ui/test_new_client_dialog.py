from __future__ import annotations

from PySide6.QtWidgets import QDialog, QMessageBox

from jr_client_archive.application.client_queries import list_clients
from jr_client_archive.domain.enums import ClientType
from jr_client_archive.ui.dialogs.new_client_dialog import NewClientDialog


def test_new_client_dialog_creates_client(qtbot, database, app_paths):
    dialog = NewClientDialog(database, username="t")
    qtbot.addWidget(dialog)

    dialog._client_type.setCurrentIndex(dialog._client_type.findData(ClientType.PERSON))
    dialog._first_name.setText("Mario")
    dialog._last_name.setText("Rossi")

    dialog._on_accept()

    assert dialog.result() == QDialog.DialogCode.Accepted
    assert dialog.created_client is not None
    assert dialog.created_client.display_name == "Mario Rossi"
    assert len(list_clients(database)) == 1


def test_new_client_dialog_rejects_missing_person_name(qtbot, database, app_paths, monkeypatch):
    dialog = NewClientDialog(database, username="t")
    qtbot.addWidget(dialog)

    dialog._client_type.setCurrentIndex(dialog._client_type.findData(ClientType.PERSON))

    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok))
    dialog._on_accept()

    assert dialog.created_client is None
    assert list_clients(database) == []


def test_new_client_dialog_requires_company_name_for_company(qtbot, database, app_paths, monkeypatch):
    dialog = NewClientDialog(database, username="t")
    qtbot.addWidget(dialog)

    dialog._client_type.setCurrentIndex(dialog._client_type.findData(ClientType.COMPANY))

    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok))
    dialog._on_accept()

    assert dialog.created_client is None
    assert list_clients(database) == []
