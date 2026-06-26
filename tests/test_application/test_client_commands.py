from __future__ import annotations

import pytest

from jr_client_archive.application.client_commands import (
    CreateClientRequest,
    create_client,
    deactivate_client,
    update_client,
)
from jr_client_archive.application.client_queries import (
    count_active_clients,
    get_client,
    list_clients,
)
from jr_client_archive.application.custom_field_commands import create_definition
from jr_client_archive.application.custom_field_queries import get_values_for_entity
from jr_client_archive.domain.client import ClientCreate, ClientUpdate
from jr_client_archive.domain.custom_field import CustomFieldDefinitionCreate
from jr_client_archive.domain.enums import CustomFieldType, EntityType


def test_create_client_creates_row_and_physical_folder(database, app_paths):
    request = CreateClientRequest(client=ClientCreate(first_name="Mario", last_name="Rossi"))
    created = create_client(database, request, username="test")

    assert created.client_code == "CLI0001"
    assert created.folder_relative_path.startswith("CLI0001_ROSSI_MARIO")
    assert (app_paths.archive_root / created.folder_relative_path).is_dir()

    fetched = get_client(database, created.id)
    assert fetched.display_name == "Mario Rossi"


def test_create_client_handles_folder_name_collision(database, app_paths):
    first = create_client(
        database, CreateClientRequest(client=ClientCreate(first_name="Mario", last_name="Rossi")), username="t"
    )
    second = create_client(
        database, CreateClientRequest(client=ClientCreate(first_name="Marco", last_name="Rossi")), username="t"
    )
    assert first.folder_relative_path != second.folder_relative_path
    assert (app_paths.archive_root / first.folder_relative_path).is_dir()
    assert (app_paths.archive_root / second.folder_relative_path).is_dir()


def test_create_client_with_custom_field_values(database, app_paths):
    field = create_definition(
        database,
        CustomFieldDefinitionCreate(
            entity_type=EntityType.CLIENT, field_key="referente", label="Referente", field_type=CustomFieldType.TEXT
        ),
        username="t",
    )
    request = CreateClientRequest(
        client=ClientCreate(first_name="Mario", last_name="Rossi"),
        custom_field_values={field.id: "Giulia Bianchi"},
    )
    created = create_client(database, request, username="t")

    values = get_values_for_entity(database, EntityType.CLIENT, created.id)
    assert values[field.id] == "Giulia Bianchi"


def test_create_client_rolls_back_folder_on_db_failure(database, app_paths, monkeypatch):
    from jr_client_archive.application import client_commands

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(client_commands, "_apply_custom_field_values", _boom)

    with pytest.raises(RuntimeError):
        create_client(
            database,
            CreateClientRequest(client=ClientCreate(first_name="Mario", last_name="Rossi")),
            username="t",
        )

    assert list(app_paths.archive_root.iterdir()) == []
    assert list_clients(database) == []


def test_update_client_does_not_touch_folder(database, app_paths):
    created = create_client(
        database, CreateClientRequest(client=ClientCreate(first_name="Mario", last_name="Rossi")), username="t"
    )
    updated = update_client(database, created.id, ClientUpdate(phone="123456"), {}, username="t")

    assert updated.phone == "123456"
    assert updated.folder_relative_path == created.folder_relative_path


def test_deactivate_client_excludes_from_active_listing(database, app_paths):
    created = create_client(
        database, CreateClientRequest(client=ClientCreate(first_name="Mario", last_name="Rossi")), username="t"
    )
    assert count_active_clients(database) == 1

    deactivate_client(database, created.id, username="t")

    assert count_active_clients(database) == 0
    assert (app_paths.archive_root / created.folder_relative_path).is_dir()
