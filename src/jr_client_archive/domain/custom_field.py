from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, model_validator

from jr_client_archive.domain.enums import CustomFieldType, EntityType


class CustomFieldDefinitionCreate(BaseModel):
    entity_type: EntityType
    field_key: str
    label: str
    field_type: CustomFieldType
    is_required: bool = False
    sort_order: int = 0
    choices: list[str] | None = None

    @model_validator(mode="after")
    def _choices_required_for_choice_type(self) -> "CustomFieldDefinitionCreate":
        if self.field_type is CustomFieldType.CHOICE and not self.choices:
            raise ValueError("A CHOICE field requires a non-empty 'choices' list")
        return self


class CustomFieldDefinitionRead(CustomFieldDefinitionCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int


class CustomFieldDefinitionUpdate(BaseModel):
    """Only label/required/choices can change after creation.

    ``field_type``, ``entity_type`` and ``field_key`` are immutable: any of
    them changing would orphan already-stored values (a NUMBER value
    sitting in ``value_number`` makes no sense if the field becomes TEXT).
    To change the type, delete the field and create a new one.
    """

    label: str | None = None
    is_required: bool | None = None
    choices: list[str] | None = None


class CustomFieldValueInput(BaseModel):
    """A single value submitted by the UI for one field on one entity.

    Only one of the typed slots is expected to be set, matching
    ``field_type`` on the corresponding definition; the repository decides
    which DB column to write based on that definition, not on which slot
    happens to be filled in.
    """

    field_definition_id: int
    value_text: str | None = None
    value_number: float | None = None
    value_date: date | None = None
    value_bool: bool | None = None
