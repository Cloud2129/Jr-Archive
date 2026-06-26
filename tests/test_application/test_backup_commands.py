from __future__ import annotations

from jr_client_archive.application.backup_commands import create_backup, list_backups, restore_backup
from jr_client_archive.application.client_commands import CreateClientRequest, create_client
from jr_client_archive.application.client_queries import list_clients
from jr_client_archive.db.models.audit import AuditLogEntry
from jr_client_archive.domain.client import ClientCreate


def _create_client(database, first_name="Mario", last_name="Rossi"):
    return create_client(
        database,
        CreateClientRequest(client=ClientCreate(first_name=first_name, last_name=last_name)),
        username="t",
    )


def test_create_backup_records_audit_entry(database, app_paths):
    info = create_backup(database, username="alice")

    assert info.path.exists()

    session = database.create_session()
    try:
        entries = session.query(AuditLogEntry).filter_by(action="backup.created").all()
        assert len(entries) == 1
        assert entries[0].username == "alice"
        assert info.path.name in entries[0].details
    finally:
        session.close()


def test_list_backups_reflects_what_was_created(database, app_paths):
    assert list_backups() == []

    info = create_backup(database, username="alice")

    backups = list_backups()
    assert [backup.path for backup in backups] == [info.path]


def test_restore_backup_records_audit_entry_and_restores_state(database, app_paths):
    _create_client(database, "Mario", "Rossi")
    info = create_backup(database, username="alice")

    _create_client(database, "Luigi", "Verdi")
    assert len(list_clients(database)) == 2

    result = restore_backup(database, info.path, username="bob")

    assert len(list_clients(database)) == 1
    assert list_clients(database)[0].display_name == "Mario Rossi"

    session = database.create_session()
    try:
        entries = session.query(AuditLogEntry).filter_by(action="backup.restored").all()
        assert len(entries) == 1
        assert entries[0].username == "bob"
        assert result.safety_backup_dir.name in entries[0].details
        assert info.path.name in entries[0].details
    finally:
        session.close()
