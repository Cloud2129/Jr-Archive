from __future__ import annotations

from sqlalchemy import select

from jr_client_archive.db.models.custom_field import CustomFieldDefinition, CustomFieldValue
from jr_client_archive.domain.enums import CustomFieldType, EntityType
from jr_client_archive.repositories.base import BaseRepository


class CustomFieldDefinitionRepository(BaseRepository[CustomFieldDefinition]):
    model = CustomFieldDefinition

    def list_for_entity(self, entity_type: EntityType) -> list[CustomFieldDefinition]:
        return list(
            self._session.scalars(
                select(CustomFieldDefinition)
                .where(CustomFieldDefinition.entity_type == entity_type)
                .order_by(CustomFieldDefinition.sort_order)
            )
        )


class CustomFieldValueRepository(BaseRepository[CustomFieldValue]):
    model = CustomFieldValue

    def list_for_entity_instance(
        self, entity_type: EntityType, entity_id: int
    ) -> list[CustomFieldValue]:
        return list(
            self._session.scalars(
                select(CustomFieldValue).where(
                    CustomFieldValue.entity_type == entity_type,
                    CustomFieldValue.entity_id == entity_id,
                )
            )
        )

    def set_value(
        self,
        definition: CustomFieldDefinition,
        entity_id: int,
        raw_value: str | float | bool | None,
    ) -> CustomFieldValue:
        """Upsert the value for one (definition, entity) pair.

        Routes ``raw_value`` into the correctly-typed column based on
        ``definition.field_type`` - the caller never needs to know which
        column that is.
        """
        existing = self._session.scalar(
            select(CustomFieldValue).where(
                CustomFieldValue.field_definition_id == definition.id,
                CustomFieldValue.entity_id == entity_id,
            )
        )
        value = existing or CustomFieldValue(
            field_definition_id=definition.id,
            entity_type=definition.entity_type,
            entity_id=entity_id,
        )
        value.value_text = None
        value.value_number = None
        value.value_date = None
        value.value_bool = None

        if definition.field_type in (CustomFieldType.TEXT, CustomFieldType.CHOICE):
            value.value_text = raw_value
        elif definition.field_type is CustomFieldType.NUMBER:
            value.value_number = raw_value
        elif definition.field_type is CustomFieldType.DATE:
            value.value_date = raw_value
        elif definition.field_type is CustomFieldType.BOOLEAN:
            value.value_bool = raw_value

        if existing is None:
            self._session.add(value)
        self._session.flush()
        return value
