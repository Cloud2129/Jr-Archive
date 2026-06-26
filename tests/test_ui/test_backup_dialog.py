from __future__ import annotations

from PySide6.QtWidgets import QMessageBox

from jr_client_archive.application.backup_commands import list_backups
from jr_client_archive.application.client_commands import CreateClientRequest, create_client
from jr_client_archive.domain.client import ClientCreate
from jr_client_archive.ui.dialogs.backup_dialog import BackupDialog


def _create_client(database, first_name="Mario", last_name="Rossi"):
    return create_client(
        database,
        CreateClientRequest(client=ClientCreate(first_name=first_name, last_name=last_name)),
        username="t",
    )


def test_no_backups_shows_placeholder(qtbot, database, app_paths):
    dialog = BackupDialog(database, username="t")
    qtbot.addWidget(dialog)

    assert dialog._backup_list.count() == 1
    assert "Nessun backup presente." in dialog._backup_list.item(0).text()


def test_create_button_adds_backup_and_refreshes_list(qtbot, database, app_paths, monkeypatch):
    dialog = BackupDialog(database, username="t")
    qtbot.addWidget(dialog)

    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))
    dialog._on_create_clicked()

    assert dialog._backup_list.count() == 1
    assert len(list_backups()) == 1
    assert dialog.restored is False


def test_restore_button_requires_a_selection(qtbot, database, app_paths, monkeypatch):
    dialog = BackupDialog(database, username="t")
    qtbot.addWidget(dialog)

    informed = {}
    monkeypatch.setattr(
        QMessageBox,
        "information",
        staticmethod(lambda *a, **k: informed.setdefault("called", True)),
    )

    dialog._on_restore_clicked()

    assert informed.get("called") is True
    assert dialog.restored is False


def test_restore_button_does_nothing_when_confirmation_declined(qtbot, database, app_paths, monkeypatch):
    _create_client(database, "Mario", "Rossi")
    dialog = BackupDialog(database, username="t")
    qtbot.addWidget(dialog)
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))
    dialog._on_create_clicked()
    dialog._backup_list.setCurrentRow(0)

    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.No))

    dialog._on_restore_clicked()

    assert dialog.restored is False


def test_restore_button_restores_state_and_sets_restored_flag(qtbot, database, app_paths, monkeypatch):
    _create_client(database, "Mario", "Rossi")
    dialog = BackupDialog(database, username="t")
    qtbot.addWidget(dialog)
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))
    dialog._on_create_clicked()
    dialog._backup_list.setCurrentRow(0)

    _create_client(database, "Luigi", "Verdi")

    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))

    dialog._on_restore_clicked()

    assert dialog.restored is True

    from jr_client_archive.application.client_queries import list_clients

    assert len(list_clients(database)) == 1
    assert list_clients(database)[0].display_name == "Mario Rossi"
