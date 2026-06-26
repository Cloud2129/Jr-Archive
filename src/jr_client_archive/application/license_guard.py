"""Shared write-gate for every application command that mutates data.

Demo restrictions (Fase 8) are enforced here rather than in the UI: each
guard raises ``LicenseRestrictionError`` and relies on the existing
``except Exception`` -> ``QMessageBox.critical`` pattern already present
in every dialog to surface the message, with no extra UI plumbing.
"""

from __future__ import annotations

from jr_client_archive.db.base import Database
from jr_client_archive.repositories.client_repository import ClientRepository
from jr_client_archive.services.license_service import LicenseService


class LicenseRestrictionError(RuntimeError):
    pass


def ensure_writable(database: Database) -> None:
    session = database.create_session()
    try:
        status = LicenseService(session).status(active_client_count=ClientRepository(session).count_active())
    finally:
        session.close()
    if status.is_read_only:
        raise LicenseRestrictionError(
            "Periodo di valutazione terminato. Attiva una licenza per continuare a modificare i dati."
        )


def ensure_can_create_client(database: Database) -> None:
    session = database.create_session()
    try:
        status = LicenseService(session).status(active_client_count=ClientRepository(session).count_active())
    finally:
        session.close()
    if status.is_read_only:
        raise LicenseRestrictionError(
            "Periodo di valutazione terminato. Attiva una licenza per continuare a modificare i dati."
        )
    if status.client_limit_reached:
        raise LicenseRestrictionError(
            f"Limite di {status.max_demo_clients} clienti raggiunto in versione demo. Attiva una licenza per continuare."
        )
