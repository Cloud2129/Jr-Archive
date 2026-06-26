from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from jr_client_archive.application.backup_commands import create_backup, restore_backup
from jr_client_archive.application.client_commands import CreateClientRequest, create_client
from jr_client_archive.application.license_guard import (
    LicenseRestrictionError,
    ensure_can_create_client,
    ensure_writable,
)
from jr_client_archive.db.models.client import Client
from jr_client_archive.db.models.license import LicenseStateRow
from jr_client_archive.domain.client import ClientCreate
from jr_client_archive.services.license_service import DEMO_DURATION_DAYS, MAX_DEMO_CLIENTS, LicenseService


def _expire_demo(database) -> None:
    session = database.create_session()
    try:
        LicenseService(session).status()  # initializes the single state row
        row = session.get(LicenseStateRow, 1)
        row.first_launch_at = datetime.now() - timedelta(days=DEMO_DURATION_DAYS + 1)
        session.commit()
    finally:
        session.close()


def _insert_active_clients(database, count: int) -> None:
    session = database.create_session()
    try:
        for i in range(count):
            session.add(
                Client(
                    client_code=f"CLI{i:04d}",
                    first_name="Test",
                    last_name=f"Client{i}",
                    folder_relative_path=f"test-client-{i}",
                    is_active=True,
                )
            )
        session.commit()
    finally:
        session.close()


def test_ensure_writable_does_not_raise_within_demo_period(database):
    ensure_writable(database)  # should not raise


def test_ensure_writable_raises_once_demo_expired(database):
    _expire_demo(database)

    with pytest.raises(LicenseRestrictionError):
        ensure_writable(database)


def test_ensure_can_create_client_raises_at_limit(database):
    _insert_active_clients(database, MAX_DEMO_CLIENTS)

    with pytest.raises(LicenseRestrictionError):
        ensure_can_create_client(database)


def test_ensure_can_create_client_does_not_raise_under_limit(database):
    _insert_active_clients(database, MAX_DEMO_CLIENTS - 1)

    ensure_can_create_client(database)  # should not raise


def test_create_client_blocked_when_limit_reached(database):
    _insert_active_clients(database, MAX_DEMO_CLIENTS)

    with pytest.raises(LicenseRestrictionError):
        create_client(
            database,
            CreateClientRequest(client=ClientCreate(first_name="One", last_name="Too Many")),
            username="t",
        )


def test_update_client_blocked_when_demo_expired(database):
    from jr_client_archive.application.client_commands import update_client
    from jr_client_archive.domain.client import ClientUpdate

    created = create_client(
        database, CreateClientRequest(client=ClientCreate(first_name="Mario", last_name="Rossi")), username="t"
    )
    _expire_demo(database)

    with pytest.raises(LicenseRestrictionError):
        update_client(database, created.id, ClientUpdate(notes="x"), {}, username="t")


def test_create_backup_remains_available_when_demo_expired(database, app_paths):
    _expire_demo(database)

    info = create_backup(database, username="t")  # should not raise

    assert info.path.exists()


def test_restore_backup_blocked_when_demo_expired(database, app_paths):
    info = create_backup(database, username="t")
    _expire_demo(database)

    with pytest.raises(LicenseRestrictionError):
        restore_backup(database, info.path, username="t")
