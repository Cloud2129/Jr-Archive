"""Fase 8 - licenza & demo, sempre verificata offline (Ed25519), mai una
chiamata di rete.

Senza una licenza attivata l'app resta interamente usabile per
``DEMO_DURATION_DAYS`` dal primo avvio (la data viene scritta una sola
volta in ``license_state.first_launch_at`` e non cambia più, nemmeno
disinstallando e reinstallando l'app sullo stesso profilo dati), con un
limite di ``MAX_DEMO_CLIENTS`` clienti creabili. Scaduto quel termine
l'app passa in sola lettura - i dati restano interamente consultabili, ma
``application.license_guard`` impedisce ad ogni comando di scrittura di
procedere, finché non si attiva una chiave valida.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from jr_client_archive.db.models.license import LicenseStateRow
from jr_client_archive.domain.license import LicenseStatus
from jr_client_archive.utils.license_signing import InvalidLicenseKeyError, verify_license

DEMO_DURATION_DAYS = 60
MAX_DEMO_CLIENTS = 150

_STATE_ROW_ID = 1


class LicenseService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def status(self, *, active_client_count: int = 0) -> LicenseStatus:
        row = self._get_or_init_state()
        is_activated, licensee = self._verify(row.license_key)

        demo_expires_at = row.first_launch_at + timedelta(days=DEMO_DURATION_DAYS)
        now = datetime.now()
        days_remaining = max(0, (demo_expires_at - now).days)
        is_demo_expired = not is_activated and now >= demo_expires_at

        return LicenseStatus(
            is_activated=is_activated,
            licensee=licensee,
            first_launch_at=row.first_launch_at,
            demo_expires_at=demo_expires_at,
            days_remaining=days_remaining,
            is_demo_expired=is_demo_expired,
            is_read_only=is_demo_expired,
            max_demo_clients=MAX_DEMO_CLIENTS,
            client_limit_reached=not is_activated and active_client_count >= MAX_DEMO_CLIENTS,
        )

    def activate(self, license_key: str) -> LicenseStatus:
        verify_license(license_key)  # raises InvalidLicenseKeyError if invalid; nothing persisted on failure
        row = self._get_or_init_state()
        row.license_key = license_key
        row.activated_at = datetime.now()
        self._session.commit()
        return self.status()

    def _get_or_init_state(self) -> LicenseStateRow:
        row = self._session.get(LicenseStateRow, _STATE_ROW_ID)
        if row is None:
            row = LicenseStateRow(id=_STATE_ROW_ID, first_launch_at=datetime.now())
            self._session.add(row)
            self._session.commit()
        return row

    def _verify(self, license_key: str | None) -> tuple[bool, str | None]:
        if license_key is None:
            return False, None
        try:
            return True, verify_license(license_key).get("licensee")
        except InvalidLicenseKeyError:
            return False, None
