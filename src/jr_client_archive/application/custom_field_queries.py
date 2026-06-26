from __future__ import annotations

from typing import Any

from jr_client_archive.db.base import Database
from jr_client_archive.domain.custom_field import CustomFieldDefinitionRead
from jr_client_archive.domain.enums import EntityType
from jr_client_archive.repositories.custom_field_repository import (
    CustomFieldDefinitionRepository,
    CustomFieldValueRepository,
    extract_python_value,
)


def list_definitions(database: Database, entity_type: EntityType) -> list[CustomFieldDefinitionRead]:
    session = database.create_session()
    try:
        definitions = CustomFieldDefinitionRepository(session).list_for_entity(entity_type)
        return [CustomFieldDefinitionRead.model_validate(d) for d in definitions]
    finally:
        session.close()


def get_values_for_entity(
    database: Database, entity_type: EntityType, entity_id: int
) -> dict[int, Any]:
    """Return ``{field_definition_id: python_value}`` for one entity
    instance, e.g. one client - exactly the shape the custom field form
    widget needs to pre-fill itself.
    """
    session = database.create_session()
    try:
        definitions = {
            d.id: d for d in CustomFieldDefinitionRepository(session).list_for_entity(entity_type)
        }
        values = CustomFieldValueRepository(session).list_for_entity_instance(entity_type, entity_id)
        return {
            value.field_definition_id: extract_python_value(
                value, definitions[value.field_definition_id].field_type
            )
            for value in values
            if value.field_definition_id in definitions
        }
    finally:
        session.close()
