"""Read-only license/demo status, consumed by the UI to show the
'versione demo' banner and by the activation dialog."""

from __future__ import annotations

from jr_client_archive.db.base import Database
from jr_client_archive.domain.license import LicenseStatus
from jr_client_archive.repositories.client_repository import ClientRepository
from jr_client_archive.services.license_service import LicenseService


def get_license_status(database: Database) -> LicenseStatus:
    session = database.create_session()
    try:
        active_clients = ClientRepository(session).count_active()
        return LicenseService(session).status(active_client_count=active_clients)
    finally:
        session.close()
