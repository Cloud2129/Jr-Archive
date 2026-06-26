"""Business-level audit trail: 'ogni accesso, ogni modifica, ogni rinomina,
ogni errore, ogni backup, ogni importazione' is expected to call
:meth:`AuditService.record`.

Deliberately the only service in Phase 1 with no UI counterpart yet: every
later phase (client CRUD, document rename, backup, import) will call into
this one, so it needs to exist and be trivially easy to call correctly
before any of those are built.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from jr_client_archive.db.models.audit import AuditLogEntry


class AuditService:
    def __init__(self, session: Session, *, username: str) -> None:
        self._session = session
        self._username = username

    def record(
        self,
        action: str,
        *,
        entity_type: str | None = None,
        entity_id: int | None = None,
        details: str | None = None,
    ) -> AuditLogEntry:
        entry = AuditLogEntry(
            occurred_at=datetime.now(),
            username=self._username,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
        )
        self._session.add(entry)
        self._session.commit()
        return entry
