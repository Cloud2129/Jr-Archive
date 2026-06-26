from __future__ import annotations

from PySide6.QtWidgets import QDialog

import jr_client_archive.ui.main_window as main_window_module
from jr_client_archive.application.client_commands import CreateClientRequest, create_client
from jr_client_archive.config.paths import AppPaths
from jr_client_archive.domain.client import ClientCreate
from jr_client_archive.ui.main_window import MainWindow


def test_new_client_button_refreshes_list(qtbot, database, app_paths, monkeypatch, tmp_path):
    paths = AppPaths(root=tmp_path)
    window = MainWindow(database=database, paths=paths)
    qtbot.addWidget(window)
    assert window._client_list.count() == 1  # "Nessun cliente" placeholder

    created = create_client(
        database, CreateClientRequest(client=ClientCreate(first_name="Mario", last_name="Rossi")), username="t"
    )

    def _fake_exec(self):
        self.created_client = created
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(main_window_module.NewClientDialog, "exec", _fake_exec)
    window._on_new_client_clicked()

    assert window._client_list.count() == 1
    assert "Mario Rossi" in window._client_list.item(0).text()


def test_license_banner_shown_during_demo(qtbot, database, app_paths, tmp_path):
    paths = AppPaths(root=tmp_path)
    window = MainWindow(database=database, paths=paths)
    qtbot.addWidget(window)

    assert "demo" in window._license_banner.text().lower()


def test_license_button_opens_dialog_and_refreshes_banner(qtbot, database, app_paths, monkeypatch, tmp_path):
    paths = AppPaths(root=tmp_path)
    window = MainWindow(database=database, paths=paths)
    qtbot.addWidget(window)

    called = {}

    def _fake_exec(self):
        called["opened"] = True
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(main_window_module.LicenseDialog, "exec", _fake_exec)
    window._on_license_clicked()

    assert called.get("opened") is True


def test_double_click_opens_dossier(qtbot, database, app_paths, monkeypatch, tmp_path):
    create_client(
        database, CreateClientRequest(client=ClientCreate(first_name="Mario", last_name="Rossi")), username="t"
    )
    paths = AppPaths(root=tmp_path)
    window = MainWindow(database=database, paths=paths)
    qtbot.addWidget(window)

    opened = {}

    def _fake_exec(self):
        opened["client"] = self._client
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(main_window_module.ClientDossierDialog, "exec", _fake_exec)
    window._on_client_double_clicked(window._client_list.item(0))

    assert opened["client"].display_name == "Mario Rossi"


def test_custom_fields_button_opens_manager(qtbot, database, app_paths, monkeypatch, tmp_path):
    paths = AppPaths(root=tmp_path)
    window = MainWindow(database=database, paths=paths)
    qtbot.addWidget(window)

    called = {}

    def _fake_exec(self):
        called["opened"] = True
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(main_window_module.CustomFieldsManagerDialog, "exec", _fake_exec)
    window._on_custom_fields_clicked()

    assert called.get("opened") is True


def test_global_search_button_opens_dialog_and_reloads_dashboard(qtbot, database, app_paths, monkeypatch, tmp_path):
    paths = AppPaths(root=tmp_path)
    window = MainWindow(database=database, paths=paths)
    qtbot.addWidget(window)

    called = {}

    def _fake_exec(self):
        called["opened"] = True
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(main_window_module.GlobalSearchDialog, "exec", _fake_exec)
    window._on_global_search_clicked()

    assert called.get("opened") is True


def test_backup_button_opens_dialog_and_reloads_only_if_restored(qtbot, database, app_paths, monkeypatch, tmp_path):
    paths = AppPaths(root=tmp_path)
    window = MainWindow(database=database, paths=paths)
    qtbot.addWidget(window)

    def _fake_exec_no_restore(self):
        self.restored = False
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(main_window_module.BackupDialog, "exec", _fake_exec_no_restore)
    window._on_backup_clicked()  # should not raise even though nothing was restored

    create_client(
        database, CreateClientRequest(client=ClientCreate(first_name="Mario", last_name="Rossi")), username="t"
    )

    def _fake_exec_restored(self):
        self.restored = True
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(main_window_module.BackupDialog, "exec", _fake_exec_restored)
    window._on_backup_clicked()

    assert window._client_list.count() == 1
    assert "Mario Rossi" in window._client_list.item(0).text()
