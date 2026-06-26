from __future__ import annotations

from jr_client_archive.application.client_commands import CreateClientRequest, create_client
from jr_client_archive.application.folder_queries import get_root_folder, list_folders_for_client
from jr_client_archive.domain.client import ClientCreate


def _create_client(database):
    return create_client(
        database, CreateClientRequest(client=ClientCreate(first_name="Mario", last_name="Rossi")), username="t"
    )


def test_get_root_folder_returns_client_root(database, app_paths):
    client = _create_client(database)
    expected_root = list_folders_for_client(database, client.id)[0]

    folder = get_root_folder(database, client.id)

    assert folder is not None
    assert folder.id == expected_root.id
    assert folder.relative_path == expected_root.relative_path


def test_get_root_folder_returns_none_for_unknown_client(database, app_paths):
    assert get_root_folder(database, 999) is None
