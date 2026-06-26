"""Use cases behind document ingestion and cataloging.

Deliberately split in two steps, matching how a user actually works:

1. ``add_document`` - a file lands in a folder. We copy it in (never
   touching the original), fingerprint it (checksum/size/extension) and
   record it as ``TO_VERIFY``. Nothing is renamed yet because the naming
   pattern needs ``document_type``/``document_date``, which aren't known
   at this point.
2. ``catalog_document`` - once the user supplies that classification, the
   document is renamed on disk (conflict-checked, never overwriting) and
   flips to ``CATALOGUED``.

The automatic client-matching/drag&drop recognition engine and the
"documents to verify" dashboard widget build on top of step 1 in a later
phase; this module only covers the explicit, already-targeted upload.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from jr_client_archive.config.paths import get_app_paths
from jr_client_archive.config.settings import SettingsService
from jr_client_archive.db.base import Database
from jr_client_archive.db.models.document import Document, DocumentHistoryEntry
from jr_client_archive.domain.client import ClientRead
from jr_client_archive.domain.document import DocumentCatalogUpdate, DocumentRead
from jr_client_archive.domain.enums import DocumentStatus, HistoryEventType
from jr_client_archive.repositories.client_repository import ClientRepository
from jr_client_archive.repositories.document_repository import DocumentRepository, TagRepository
from jr_client_archive.repositories.folder_repository import FolderRepository
from jr_client_archive.services.audit_service import AuditService
from jr_client_archive.services.filesystem_service import FilesystemService
from jr_client_archive.utils.checksums import sha256_file
from jr_client_archive.utils.document_naming import render_document_stem


def add_document(
    database: Database, client_id: int, folder_id: int, source_path: Path, *, username: str
) -> DocumentRead:
    archive_root = get_app_paths().archive_root
    fs_service = FilesystemService(archive_root)

    session = database.create_session()
    try:
        folder = FolderRepository(session).get(folder_id)
        if folder is None or folder.client_id != client_id:
            raise ValueError("Cartella non valida per questo cliente.")
        if ClientRepository(session).get(client_id) is None:
            raise ValueError(f"Cliente {client_id} non trovato.")

        extension = source_path.suffix.lstrip(".").lower()
        relative_path = fs_service.copy_document_into_folder(
            source_path, folder.relative_path, source_path.stem, extension
        )
        absolute_path = archive_root / relative_path

        document = Document(
            client_id=client_id,
            folder_id=folder_id,
            original_filename=source_path.name,
            stored_filename=absolute_path.name,
            relative_path=relative_path,
            extension=extension,
            size_bytes=absolute_path.stat().st_size,
            checksum_sha256=sha256_file(absolute_path),
            uploaded_at=datetime.now(),
            uploaded_by=username,
            status=DocumentStatus.TO_VERIFY,
        )
        DocumentRepository(session).add(document)
        document.history.append(
            DocumentHistoryEntry(
                event_type=HistoryEventType.CREATED,
                new_value=document.stored_filename,
                performed_by=username,
                occurred_at=datetime.now(),
            )
        )
        session.flush()

        AuditService(session, username=username).record(
            "document.created", entity_type="DOCUMENT", entity_id=document.id,
            details=f"Documento '{source_path.name}' caricato in {folder.relative_path}",
        )
        return DocumentRead.from_orm_document(document)
    finally:
        session.close()


def catalog_document(
    database: Database, document_id: int, payload: DocumentCatalogUpdate, *, username: str
) -> DocumentRead:
    archive_root = get_app_paths().archive_root
    fs_service = FilesystemService(archive_root)

    session = database.create_session()
    try:
        document = DocumentRepository(session).get(document_id)
        if document is None:
            raise ValueError(f"Documento {document_id} non trovato.")

        client = ClientRepository(session).get(document.client_id)
        if client is None:
            raise ValueError(f"Cliente {document.client_id} non trovato.")

        document.document_type = payload.document_type
        document.category = payload.category
        document.description = payload.description
        document.document_date = payload.document_date
        document.tags = TagRepository(session).get_or_create_many(payload.tags)

        settings = SettingsService(session).load()
        new_stem = render_document_stem(
            settings.document_naming_pattern,
            client=ClientRead.model_validate(client),
            document_type=payload.document_type,
            category=payload.category,
            document_date=payload.document_date,
        )

        old_relative_path = document.relative_path
        new_relative_path = fs_service.rename_document(old_relative_path, new_stem)
        if new_relative_path != old_relative_path:
            document.relative_path = new_relative_path
            document.stored_filename = Path(new_relative_path).name
            document.history.append(
                DocumentHistoryEntry(
                    event_type=HistoryEventType.RENAMED,
                    old_value=old_relative_path,
                    new_value=new_relative_path,
                    performed_by=username,
                    occurred_at=datetime.now(),
                )
            )

        document.status = DocumentStatus.CATALOGUED
        document.history.append(
            DocumentHistoryEntry(
                event_type=HistoryEventType.CATALOGUED,
                new_value=payload.document_type,
                performed_by=username,
                occurred_at=datetime.now(),
            )
        )
        session.flush()

        AuditService(session, username=username).record(
            "document.catalogued", entity_type="DOCUMENT", entity_id=document.id,
        )
        return DocumentRead.from_orm_document(document)
    finally:
        session.close()
