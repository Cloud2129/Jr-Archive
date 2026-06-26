"""Reconciles the database after a document or folder gets renamed/moved
outside the app (Explorer, Finder, a script, ...).

Fed by ``FolderWatchService``, which only ever reports moves - see that
module's docstring for why creations/deletions are deliberately ignored.
The change is recorded in the document/audit history exactly like a
rename performed through the UI would be, just attributed to
``EXTERNAL_SYNC_ACTOR`` instead of a real username, so "conservare la
cronologia delle modifiche" holds for externally-triggered changes too.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import PurePosixPath

from sqlalchemy import select
from sqlalchemy.orm import Session

from jr_client_archive.db.base import Database
from jr_client_archive.db.models.document import Document, DocumentHistoryEntry
from jr_client_archive.db.models.folder import Folder
from jr_client_archive.domain.enums import HistoryEventType
from jr_client_archive.repositories.client_repository import ClientRepository
from jr_client_archive.repositories.document_repository import DocumentRepository
from jr_client_archive.repositories.folder_repository import FolderRepository
from jr_client_archive.services.audit_service import AuditService

EXTERNAL_SYNC_ACTOR = "Sincronizzazione esterna"


def reconcile_external_move(
    database: Database, old_relative_path: str, new_relative_path: str, *, is_directory: bool
) -> bool:
    """Updates whichever document/folder used to live at
    ``old_relative_path``. Returns ``True`` if something was reconciled,
    ``False`` if the path wasn't tracked (e.g. a stray file moved directly
    on disk that was never ingested through the app).
    """
    session = database.create_session()
    try:
        if is_directory:
            return _reconcile_folder(session, old_relative_path, new_relative_path)
        return _reconcile_document(session, old_relative_path, new_relative_path)
    finally:
        session.close()


def _reconcile_document(session: Session, old_relative_path: str, new_relative_path: str) -> bool:
    document = DocumentRepository(session).get_by_relative_path(old_relative_path)
    if document is None:
        return False

    moved_to_different_folder = PurePosixPath(old_relative_path).parent != PurePosixPath(new_relative_path).parent
    event_type = HistoryEventType.MOVED if moved_to_different_folder else HistoryEventType.RENAMED

    document.relative_path = new_relative_path
    document.stored_filename = PurePosixPath(new_relative_path).name
    document.history.append(
        DocumentHistoryEntry(
            event_type=event_type,
            old_value=old_relative_path,
            new_value=new_relative_path,
            performed_by=EXTERNAL_SYNC_ACTOR,
            occurred_at=datetime.now(),
        )
    )
    session.flush()

    AuditService(session, username=EXTERNAL_SYNC_ACTOR).record(
        "document.external_sync",
        entity_type="DOCUMENT",
        entity_id=document.id,
        details=f"Rilevata modifica esterna: '{old_relative_path}' -> '{new_relative_path}'",
    )
    return True


def _reconcile_folder(session: Session, old_relative_path: str, new_relative_path: str) -> bool:
    folder = FolderRepository(session).get_by_relative_path(old_relative_path)
    if folder is None:
        return False

    prefix = f"{old_relative_path}/"
    folder.relative_path = new_relative_path
    folder.name = PurePosixPath(new_relative_path).name

    for descendant in session.scalars(select(Folder).where(Folder.id != folder.id)):
        if descendant.relative_path.startswith(prefix):
            descendant.relative_path = new_relative_path + descendant.relative_path[len(old_relative_path) :]

    for document in session.scalars(select(Document)):
        if not document.relative_path.startswith(prefix):
            continue
        old_document_path = document.relative_path
        document.relative_path = new_relative_path + document.relative_path[len(old_relative_path) :]
        document.stored_filename = PurePosixPath(document.relative_path).name
        document.history.append(
            DocumentHistoryEntry(
                event_type=HistoryEventType.MOVED,
                old_value=old_document_path,
                new_value=document.relative_path,
                performed_by=EXTERNAL_SYNC_ACTOR,
                occurred_at=datetime.now(),
            )
        )

    if folder.parent_id is None:
        client = ClientRepository(session).get(folder.client_id)
        if client is not None:
            client.folder_relative_path = new_relative_path

    session.flush()

    AuditService(session, username=EXTERNAL_SYNC_ACTOR).record(
        "folder.external_sync",
        entity_type="FOLDER",
        entity_id=folder.id,
        details=f"Rilevata modifica esterna: '{old_relative_path}' -> '{new_relative_path}'",
    )
    return True
