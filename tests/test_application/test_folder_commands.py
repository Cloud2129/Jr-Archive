from __future__ import annotations

import pytest

from jr_client_archive.application.client_commands import CreateClientRequest, create_client
from jr_client_archive.application.folder_commands import create_subfolder
from jr_client_archive.application.folder_queries import list_folders_for_client
from jr_client_archive.domain.client import ClientCreate


def _create_client(database):
    return create_client(
        database, CreateClientRequest(client=ClientCreate(first_name="Mario", last_name="Rossi")), username="t"
    )


def test_create_subfolder_under_client_root(database, app_paths):
    client = _create_client(database)
    root_folder = list_folders_for_client(database, client.id)[0]

    subfolder = create_subfolder(database, client.id, root_folder.id, "Contratti", username="t")

    assert subfolder.relative_path == f"{root_folder.relative_path}/CONTRATTI"
    assert (app_paths.archive_root / subfolder.relative_path).is_dir()

    all_folders = list_folders_for_client(database, client.id)
    assert {f.relative_path for f in all_folders} == {root_folder.relative_path, subfolder.relative_path}


def test_create_subfolder_conflict_raises(database, app_paths):
    client = _create_client(database)
    root_folder = list_folders_for_client(database, client.id)[0]

    create_subfolder(database, client.id, root_folder.id, "Contratti", username="t")
    with pytest.raises(FileExistsError):
        create_subfolder(database, client.id, root_folder.id, "Contratti", username="t")


def test_create_subfolder_rejects_parent_from_another_client(database, app_paths):
    client_a = _create_client(database)
    client_b = create_client(
        database, CreateClientRequest(client=ClientCreate(first_name="Luigi", last_name="Verdi")), username="t"
    )
    root_folder_b = list_folders_for_client(database, client_b.id)[0]

    with pytest.raises(ValueError):
        create_subfolder(database, client_a.id, root_folder_b.id, "Contratti", username="t")
