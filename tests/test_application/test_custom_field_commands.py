from __future__ import annotations

from jr_client_archive.application.custom_field_commands import (
    create_definition,
    delete_definition,
    move_definition,
    update_definition,
)
from jr_client_archive.application.custom_field_queries import list_definitions
from jr_client_archive.domain.custom_field import CustomFieldDefinitionCreate, CustomFieldDefinitionUpdate
from jr_client_archive.domain.enums import CustomFieldType, EntityType


def _create(database, key: str, label: str, **overrides):
    return create_definition(
        database,
        CustomFieldDefinitionCreate(
            entity_type=EntityType.CLIENT, field_key=key, label=label, field_type=CustomFieldType.TEXT, **overrides
        ),
        username="t",
    )


def test_new_definitions_append_to_end_of_sort_order(database):
    first = _create(database, "primo", "Primo")
    second = _create(database, "secondo", "Secondo")
    assert first.sort_order == 0
    assert second.sort_order == 1


def test_move_definition_swaps_with_neighbor(database):
    first = _create(database, "primo", "Primo")
    second = _create(database, "secondo", "Secondo")

    reordered = move_definition(database, second.id, "up", username="t")
    assert [d.field_key for d in reordered] == ["secondo", "primo"]

    reordered_again = move_definition(database, second.id, "up", username="t")
    assert [d.field_key for d in reordered_again] == ["secondo", "primo"]


def test_update_definition_changes_label_and_required(database):
    field = _create(database, "referente", "Referente")
    updated = update_definition(
        database, field.id, CustomFieldDefinitionUpdate(label="Referente principale", is_required=True), username="t"
    )
    assert updated.label == "Referente principale"
    assert updated.is_required is True


def test_delete_definition_removes_it_from_list(database):
    field = _create(database, "temporaneo", "Temporaneo")
    delete_definition(database, field.id, username="t")
    assert list_definitions(database, EntityType.CLIENT) == []
