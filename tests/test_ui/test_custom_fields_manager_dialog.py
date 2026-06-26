from __future__ import annotations

from PySide6.QtWidgets import QDialog, QMessageBox

import jr_client_archive.ui.dialogs.custom_fields_manager_dialog as manager_module
from jr_client_archive.application.custom_field_commands import create_definition
from jr_client_archive.application.custom_field_queries import list_definitions
from jr_client_archive.domain.custom_field import CustomFieldDefinitionCreate
from jr_client_archive.domain.enums import CustomFieldType, EntityType
from jr_client_archive.ui.dialogs.custom_fields_manager_dialog import CustomFieldsManagerDialog


def _patch_field_edit_dialog(monkeypatch, **field_values):
    defaults = {
        "field_key": "referente",
        "label": "Referente",
        "field_type": CustomFieldType.TEXT,
        "is_required": False,
        "choices": None,
    }
    defaults.update(field_values)
    monkeypatch.setattr(manager_module._FieldEditDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
    for name, value in defaults.items():
        monkeypatch.setattr(manager_module._FieldEditDialog, name, lambda self, v=value: v)


def test_on_add_creates_definition(qtbot, database, monkeypatch):
    dialog = CustomFieldsManagerDialog(database, EntityType.CLIENT, username="t")
    qtbot.addWidget(dialog)

    _patch_field_edit_dialog(monkeypatch)
    dialog._on_add()

    assert dialog._list.count() == 1
    assert len(list_definitions(database, EntityType.CLIENT)) == 1


def test_on_edit_updates_label_and_required(qtbot, database, monkeypatch):
    create_definition(
        database,
        CustomFieldDefinitionCreate(
            entity_type=EntityType.CLIENT, field_key="referente", label="Referente", field_type=CustomFieldType.TEXT
        ),
        username="t",
    )
    dialog = CustomFieldsManagerDialog(database, EntityType.CLIENT, username="t")
    qtbot.addWidget(dialog)
    dialog._list.setCurrentRow(0)

    _patch_field_edit_dialog(monkeypatch, label="Referente principale", is_required=True)
    dialog._on_edit()

    updated = list_definitions(database, EntityType.CLIENT)[0]
    assert updated.label == "Referente principale"
    assert updated.is_required is True


def test_on_delete_removes_definition(qtbot, database, monkeypatch):
    create_definition(
        database,
        CustomFieldDefinitionCreate(
            entity_type=EntityType.CLIENT, field_key="temp", label="Temp", field_type=CustomFieldType.TEXT
        ),
        username="t",
    )
    dialog = CustomFieldsManagerDialog(database, EntityType.CLIENT, username="t")
    qtbot.addWidget(dialog)
    dialog._list.setCurrentRow(0)

    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))
    dialog._on_delete()

    assert list_definitions(database, EntityType.CLIENT) == []


def test_on_move_swaps_order(qtbot, database):
    create_definition(
        database,
        CustomFieldDefinitionCreate(
            entity_type=EntityType.CLIENT, field_key="primo", label="Primo", field_type=CustomFieldType.TEXT
        ),
        username="t",
    )
    create_definition(
        database,
        CustomFieldDefinitionCreate(
            entity_type=EntityType.CLIENT, field_key="secondo", label="Secondo", field_type=CustomFieldType.TEXT
        ),
        username="t",
    )
    dialog = CustomFieldsManagerDialog(database, EntityType.CLIENT, username="t")
    qtbot.addWidget(dialog)
    dialog._list.setCurrentRow(1)

    dialog._on_move("up")

    ordered = list_definitions(database, EntityType.CLIENT)
    assert [d.field_key for d in ordered] == ["secondo", "primo"]
