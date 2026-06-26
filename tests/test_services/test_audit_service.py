from __future__ import annotations

from jr_client_archive.db.models.audit import AuditLogEntry
from jr_client_archive.services.audit_service import AuditService


def test_record_persists_entry_with_username_and_details(database):
    session = database.create_session()
    service = AuditService(session, username="jurij")

    service.record(
        "client.created",
        entity_type="CLIENT",
        entity_id=1,
        details="Creato cliente CLI0001",
    )

    entries = session.query(AuditLogEntry).all()
    assert len(entries) == 1
    assert entries[0].username == "jurij"
    assert entries[0].action == "client.created"
    assert entries[0].entity_id == 1
