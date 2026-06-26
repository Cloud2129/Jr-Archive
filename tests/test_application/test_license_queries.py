from __future__ import annotations

from jr_client_archive.application.client_commands import CreateClientRequest, create_client
from jr_client_archive.application.license_queries import get_license_status
from jr_client_archive.domain.client import ClientCreate


def test_get_license_status_reflects_active_client_count(database):
    status = get_license_status(database)
    assert status.client_limit_reached is False
    assert status.is_activated is False

    create_client(
        database, CreateClientRequest(client=ClientCreate(first_name="Mario", last_name="Rossi")), username="t"
    )

    status = get_license_status(database)
    assert status.days_remaining > 0
