from __future__ import annotations

from jr_client_archive.config.paths import AppPaths
from jr_client_archive.db.models.client import Client
from jr_client_archive.domain.enums import ClientType
from jr_client_archive.repositories.client_repository import ClientRepository
from jr_client_archive.ui.main_window import MainWindow


def test_main_window_boots_with_empty_database(qtbot, database, tmp_path):
    paths = AppPaths(root=tmp_path)
    window = MainWindow(database=database, paths=paths)
    qtbot.addWidget(window)

    assert window.windowTitle().startswith("JR Client Archive")
    assert window._client_list.count() == 1
    assert "Nessun cliente" in window._client_list.item(0).text()


def test_main_window_lists_and_filters_clients(qtbot, database, tmp_path):
    session = database.create_session()
    repo = ClientRepository(session)
    repo.add(
        Client(
            client_code=repo.next_client_code(),
            client_type=ClientType.PERSON,
            first_name="Mario",
            last_name="Rossi",
            folder_relative_path="CLI0001_ROSSI_MARIO",
        )
    )
    session.commit()

    paths = AppPaths(root=tmp_path)
    window = MainWindow(database=database, paths=paths)
    qtbot.addWidget(window)

    assert window._client_list.count() == 1
    assert "Mario Rossi" in window._client_list.item(0).text()

    window._search_box.setText("nessun risultato")
    assert "Nessun cliente" in window._client_list.item(0).text()

    window._search_box.setText("rossi")
    assert "Mario Rossi" in window._client_list.item(0).text()
