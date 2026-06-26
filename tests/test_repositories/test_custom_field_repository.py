from __future__ import annotations

from datetime import date

from jr_client_archive.db.models.client import Client
from jr_client_archive.db.models.custom_field import CustomFieldDefinition
from jr_client_archive.domain.enums import ClientType, CustomFieldType, EntityType
from jr_client_archive.repositories.client_repository import ClientRepository
from jr_client_archive.repositories.custom_field_repository import (
    CustomFieldDefinitionRepository,
    CustomFieldValueRepository,
)


def _make_client(session) -> Client:
    repo = ClientRepository(session)
    client = repo.add(
        Client(
            client_code=repo.next_client_code(),
            client_type=ClientType.PERSON,
            first_name="Mario",
            last_name="Rossi",
            folder_relative_path="CLI0001_ROSSI_MARIO",
        )
    )
    session.commit()
    return client


def test_custom_field_definition_and_typed_value_roundtrip(database):
    session = database.create_session()
    client = _make_client(session)

    definitions = CustomFieldDefinitionRepository(session)
    values = CustomFieldValueRepository(session)

    text_field = definitions.add(
        CustomFieldDefinition(
            entity_type=EntityType.CLIENT,
            field_key="referente",
            label="Referente",
            field_type=CustomFieldType.TEXT,
        )
    )
    date_field = definitions.add(
        CustomFieldDefinition(
            entity_type=EntityType.CLIENT,
            field_key="scadenza_incarico",
            label="Scadenza incarico",
            field_type=CustomFieldType.DATE,
        )
    )
    session.commit()

    values.set_value(text_field, client.id, "Giulia Bianchi")
    values.set_value(date_field, client.id, date(2026, 12, 31))
    session.commit()

    stored = values.list_for_entity_instance(EntityType.CLIENT, client.id)
    by_field = {v.field_definition_id: v for v in stored}

    assert by_field[text_field.id].value_text == "Giulia Bianchi"
    assert by_field[date_field.id].value_date == date(2026, 12, 31)


def test_set_value_upserts_instead_of_duplicating(database):
    session = database.create_session()
    client = _make_client(session)
    definitions = CustomFieldDefinitionRepository(session)
    values = CustomFieldValueRepository(session)

    field = definitions.add(
        CustomFieldDefinition(
            entity_type=EntityType.CLIENT,
            field_key="note_extra",
            label="Note extra",
            field_type=CustomFieldType.TEXT,
        )
    )
    session.commit()

    values.set_value(field, client.id, "prima versione")
    values.set_value(field, client.id, "versione aggiornata")
    session.commit()

    stored = values.list_for_entity_instance(EntityType.CLIENT, client.id)
    assert len(stored) == 1
    assert stored[0].value_text == "versione aggiornata"


def test_list_for_entity_returns_definitions_ordered_by_sort_order(database):
    session = database.create_session()
    definitions = CustomFieldDefinitionRepository(session)

    definitions.add(
        CustomFieldDefinition(
            entity_type=EntityType.CLIENT,
            field_key="secondo",
            label="Secondo",
            field_type=CustomFieldType.TEXT,
            sort_order=2,
        )
    )
    definitions.add(
        CustomFieldDefinition(
            entity_type=EntityType.CLIENT,
            field_key="primo",
            label="Primo",
            field_type=CustomFieldType.TEXT,
            sort_order=1,
        )
    )
    session.commit()

    ordered = definitions.list_for_entity(EntityType.CLIENT)
    assert [d.field_key for d in ordered] == ["primo", "secondo"]
