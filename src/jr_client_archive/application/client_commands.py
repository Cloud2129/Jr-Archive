"""Use cases behind client creation/editing.

This is the one place that coordinates "create the DB row, create the
physical folder, store the custom field values, write the audit entry" as
a single unit: if anything fails partway through, the transaction rolls
back *and* the folder just created on disk is removed, so we never end up
with a client row pointing at a folder that doesn't exist (or vice versa).
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from jr_client_archive.config.paths import get_app_paths
from jr_client_archive.db.base import Database
from jr_client_archive.db.models.client import Client
from jr_client_archive.db.models.folder import Folder
from jr_client_archive.domain.client import ClientCreate, ClientRead, ClientUpdate
from jr_client_archive.domain.enums import EntityType
from jr_client_archive.repositories.client_repository import ClientRepository
from jr_client_archive.repositories.custom_field_repository import (
    CustomFieldDefinitionRepository,
    CustomFieldValueRepository,
)
from jr_client_archive.repositories.folder_repository import FolderRepository
from jr_client_archive.services.audit_service import AuditService
from jr_client_archive.services.filesystem_service import FilesystemService
from jr_client_archive.utils.text import build_folder_name


@dataclass
class CreateClientRequest:
    client: ClientCreate
    custom_field_values: dict[int, Any] = field(default_factory=dict)


def create_client(database: Database, request: CreateClientRequest, *, username: str) -> ClientRead:
    archive_root = get_app_paths().archive_root
    fs_service = FilesystemService(archive_root)

    session = database.create_session()
    try:
        client_repo = ClientRepository(session)
        code = client_repo.next_client_code()

        name_parts = (
            (request.client.last_name, request.client.first_name)
            if request.client.company_name is None
            else (request.client.company_name,)
        )
        folder_name = build_folder_name(code, *name_parts)
        relative_path = fs_service.create_client_root_folder(folder_name)

        try:
            client = client_repo.add(
                Client(client_code=code, folder_relative_path=relative_path, **request.client.model_dump())
            )
            session.flush()

            FolderRepository(session).add(
                Folder(
                    client_id=client.id,
                    parent_id=None,
                    name=folder_name,
                    relative_path=relative_path,
                    is_auto_generated=True,
                )
            )

            _apply_custom_field_values(session, client.id, request.custom_field_values)

            AuditService(session, username=username).record(
                "client.created", entity_type="CLIENT", entity_id=client.id,
                details=f"Cliente {code} ({client.display_name}) creato",
            )
            return ClientRead.model_validate(client)
        except Exception:
            session.rollback()
            shutil.rmtree(archive_root / relative_path, ignore_errors=True)
            raise
    finally:
        session.close()


def update_client(
    database: Database,
    client_id: int,
    payload: ClientUpdate,
    custom_field_values: dict[int, Any],
    *,
    username: str,
) -> ClientRead:
    """Updates anagrafica fields and custom field values.

    Deliberately does not touch ``folder_relative_path``: renaming a
    client never silently renames/moves their physical folder. Folder
    operations go through ``application.folder_commands`` explicitly.
    """
    session = database.create_session()
    try:
        repo = ClientRepository(session)
        client = repo.get(client_id)
        if client is None:
            raise ValueError(f"Cliente {client_id} non trovato.")

        for attr, value in payload.model_dump(exclude_unset=True).items():
            setattr(client, attr, value)
        session.flush()

        _apply_custom_field_values(session, client.id, custom_field_values)

        AuditService(session, username=username).record(
            "client.updated", entity_type="CLIENT", entity_id=client.id,
        )
        return ClientRead.model_validate(client)
    finally:
        session.close()


def deactivate_client(database: Database, client_id: int, *, username: str) -> None:
    """Marks a client inactive. Never deletes the row, the folder, or any
    document - consistent with the rule that nothing is removed without
    an explicit, separate action.
    """
    session = database.create_session()
    try:
        repo = ClientRepository(session)
        client = repo.get(client_id)
        if client is None:
            return
        client.is_active = False
        session.flush()
        AuditService(session, username=username).record(
            "client.deactivated", entity_type="CLIENT", entity_id=client_id,
        )
    finally:
        session.close()


def _apply_custom_field_values(session: Session, client_id: int, values: dict[int, Any]) -> None:
    if not values:
        return
    definition_repo = CustomFieldDefinitionRepository(session)
    value_repo = CustomFieldValueRepository(session)
    for definition_id, raw_value in values.items():
        definition = definition_repo.get(definition_id)
        if definition is not None and definition.entity_type is EntityType.CLIENT:
            value_repo.set_value(definition, client_id, raw_value)
