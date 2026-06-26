from __future__ import annotations

from jr_client_archive.application.client_commands import CreateClientRequest, create_client
from jr_client_archive.application.client_queries import get_client
from jr_client_archive.application.custom_field_commands import create_definition
from jr_client_archive.application.folder_queries import list_folders_for_client
from jr_client_archive.domain.client import ClientCreate
from jr_client_archive.domain.custom_field import CustomFieldDefinitionCreate
from jr_client_archive.domain.enums import CustomFieldType, EntityType
from jr_client_archive.ui.dialogs.client_dossier_dialog import ClientDossierDialog


def _create_client(database):
    return create_client(
        database, CreateClientRequest(client=ClientCreate(first_name="Mario", last_name="Rossi")), username="t"
    )


def test_dossier_loads_anagrafica_and_root_folder(qtbot, database, app_paths):
    client = _create_client(database)
    dialog = ClientDossierDialog(database, client, username="t")
    qtbot.addWidget(dialog)

    assert dialog._first_name.text() == "Mario"
    assert dialog._last_name.text() == "Rossi"
    assert dialog._folder_tree.topLevelItemCount() == 1


def test_dossier_prefills_custom_field_values(qtbot, database, app_paths):
    field = create_definition(
        database,
        CustomFieldDefinitionCreate(
            entity_type=EntityType.CLIENT, field_key="referente", label="Referente", field_type=CustomFieldType.TEXT
        ),
        username="t",
    )
    client = create_client(
        database,
        CreateClientRequest(
            client=ClientCreate(first_name="Mario", last_name="Rossi"),
            custom_field_values={field.id: "Giulia Bianchi"},
        ),
        username="t",
    )
    dialog = ClientDossierDialog(database, client, username="t")
    qtbot.addWidget(dialog)

    assert dialog._custom_field_form.values()[field.id] == "Giulia Bianchi"


def test_dossier_creates_subfolder_under_selected_root(qtbot, database, app_paths, monkeypatch):
    client = _create_client(database)
    dialog = ClientDossierDialog(database, client, username="t")
    qtbot.addWidget(dialog)

    root_item = dialog._folder_tree.topLevelItem(0)
    dialog._folder_tree.setCurrentItem(root_item)

    from PySide6.QtWidgets import QInputDialog

    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("Contratti", True)))
    dialog._on_new_subfolder()

    folders = list_folders_for_client(database, client.id)
    assert len(folders) == 2
    assert dialog._folder_tree.topLevelItem(0).childCount() == 1


def test_dossier_save_updates_client(qtbot, database, app_paths):
    client = _create_client(database)
    dialog = ClientDossierDialog(database, client, username="t")
    qtbot.addWidget(dialog)

    dialog._phone.setText("123456")
    dialog._on_save()

    updated = get_client(database, client.id)
    assert updated.phone == "123456"
