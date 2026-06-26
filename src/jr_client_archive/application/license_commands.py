"""Use case behind the 'Attiva licenza' dialog."""

from __future__ import annotations

from jr_client_archive.db.base import Database
from jr_client_archive.domain.license import LicenseStatus
from jr_client_archive.services.audit_service import AuditService
from jr_client_archive.services.license_service import LicenseService


def activate_license(database: Database, license_key: str, *, username: str) -> LicenseStatus:
    session = database.create_session()
    try:
        status = LicenseService(session).activate(license_key)
        details = f"Licenza attivata per '{status.licensee}'" if status.licensee else "Licenza attivata"
        AuditService(session, username=username).record("license.activated", entity_type="LICENSE", details=details)
        return status
    finally:
        session.close()
