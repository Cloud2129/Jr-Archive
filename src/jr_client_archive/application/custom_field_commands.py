"""Use cases behind the 'Campi personalizzati' management screen.

The user story is explicit: add fields, delete fields, reorder them, make
them required, choose a type - all from the UI, never by touching the
database by hand. Each function here is one button in that screen.
"""

from __future__ import annotations

from jr_client_archive.application.license_guard import ensure_writable
from jr_client_archive.db.base import Database
from jr_client_archive.db.models.custom_field import CustomFieldDefinition
from jr_client_archive.domain.custom_field import (
    CustomFieldDefinitionCreate,
    CustomFieldDefinitionRead,
    CustomFieldDefinitionUpdate,
)
from jr_client_archive.repositories.custom_field_repository import CustomFieldDefinitionRepository
from jr_client_archive.services.audit_service import AuditService


def create_definition(
    database: Database, payload: CustomFieldDefinitionCreate, *, username: str
) -> CustomFieldDefinitionRead:
    ensure_writable(database)
    session = database.create_session()
    try:
        repo = CustomFieldDefinitionRepository(session)
        next_sort_order = len(repo.list_for_entity(payload.entity_type))
        data = payload.model_dump() | {"sort_order": next_sort_order}
        definition = repo.add(CustomFieldDefinition(**data))
        AuditService(session, username=username).record(
            "custom_field.created", entity_type="CUSTOM_FIELD_DEFINITION", entity_id=definition.id,
            details=f"Campo '{definition.label}' creato",
        )
        return CustomFieldDefinitionRead.model_validate(definition)
    finally:
        session.close()


def update_definition(
    database: Database, definition_id: int, payload: CustomFieldDefinitionUpdate, *, username: str
) -> CustomFieldDefinitionRead:
    ensure_writable(database)
    session = database.create_session()
    try:
        repo = CustomFieldDefinitionRepository(session)
        definition = repo.get(definition_id)
        if definition is None:
            raise ValueError(f"Campo personalizzato {definition_id} non trovato.")

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(definition, field, value)
        session.flush()

        AuditService(session, username=username).record(
            "custom_field.updated", entity_type="CUSTOM_FIELD_DEFINITION", entity_id=definition.id,
        )
        return CustomFieldDefinitionRead.model_validate(definition)
    finally:
        session.close()


def delete_definition(database: Database, definition_id: int, *, username: str) -> None:
    """Deletes the field definition and, via cascade, every value stored
    for it. This removes metadata the user explicitly asked to remove -
    it does not touch any document or folder on disk, which the 'never
    delete automatically' rule is actually about.
    """
    ensure_writable(database)
    session = database.create_session()
    try:
        repo = CustomFieldDefinitionRepository(session)
        definition = repo.get(definition_id)
        if definition is None:
            return
        label = definition.label
        repo.delete(definition)
        AuditService(session, username=username).record(
            "custom_field.deleted", entity_type="CUSTOM_FIELD_DEFINITION", entity_id=definition_id,
            details=f"Campo '{label}' eliminato",
        )
    finally:
        session.close()


def move_definition(
    database: Database, definition_id: int, direction: str, *, username: str
) -> list[CustomFieldDefinitionRead]:
    """Swap ``sort_order`` with the neighboring field in the requested
    direction ('up' or 'down'). Returns the full, freshly-ordered list so
    the UI can just redraw from the result.
    """
    ensure_writable(database)
    session = database.create_session()
    try:
        repo = CustomFieldDefinitionRepository(session)
        definition = repo.get(definition_id)
        if definition is None:
            raise ValueError(f"Campo personalizzato {definition_id} non trovato.")

        ordered = repo.list_for_entity(definition.entity_type)
        index = ordered.index(definition)
        target_index = index - 1 if direction == "up" else index + 1
        if 0 <= target_index < len(ordered):
            neighbor = ordered[target_index]
            definition.sort_order, neighbor.sort_order = neighbor.sort_order, definition.sort_order
            session.flush()

        AuditService(session, username=username).record(
            "custom_field.reordered", entity_type="CUSTOM_FIELD_DEFINITION", entity_id=definition_id,
        )
        refreshed = repo.list_for_entity(definition.entity_type)
        return [CustomFieldDefinitionRead.model_validate(d) for d in refreshed]
    finally:
        session.close()
