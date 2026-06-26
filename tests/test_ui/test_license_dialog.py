from __future__ import annotations

from datetime import datetime, timedelta

from PySide6.QtWidgets import QMessageBox

from jr_client_archive.db.models.license import LicenseStateRow
from jr_client_archive.services.license_service import DEMO_DURATION_DAYS, LicenseService
from jr_client_archive.ui.dialogs.license_dialog import LicenseDialog
from jr_client_archive.utils.license_signing import generate_keypair, sign_license


def test_shows_demo_status_within_demo_period(qtbot, database):
    dialog = LicenseDialog(database, username="t")
    qtbot.addWidget(dialog)

    assert "demo" in dialog._status_label.text().lower()


def test_shows_expired_status_after_demo_period(qtbot, database):
    session = database.create_session()
    try:
        LicenseService(session).status()
        row = session.get(LicenseStateRow, 1)
        row.first_launch_at = datetime.now() - timedelta(days=DEMO_DURATION_DAYS + 1)
        session.commit()
    finally:
        session.close()

    dialog = LicenseDialog(database, username="t")
    qtbot.addWidget(dialog)

    assert "sola lettura" in dialog._status_label.text().lower()


def test_activate_with_empty_key_shows_information(qtbot, database, monkeypatch):
    dialog = LicenseDialog(database, username="t")
    qtbot.addWidget(dialog)

    informed = {}
    monkeypatch.setattr(
        QMessageBox, "information", staticmethod(lambda *a, **k: informed.setdefault("called", True))
    )

    dialog._on_activate_clicked()

    assert informed.get("called") is True


def test_activate_with_invalid_key_shows_error(qtbot, database, monkeypatch):
    dialog = LicenseDialog(database, username="t")
    qtbot.addWidget(dialog)
    dialog._key_input.setPlainText("not-a-valid-key")

    errored = {}
    monkeypatch.setattr(QMessageBox, "critical", staticmethod(lambda *a, **k: errored.setdefault("called", True)))

    dialog._on_activate_clicked()

    assert errored.get("called") is True


def test_activate_with_valid_key_updates_status(qtbot, database, monkeypatch):
    private_key_b64, public_key_b64 = generate_keypair()
    key = sign_license({"licensee": "Studio Rossi"}, private_key_b64=private_key_b64)

    from jr_client_archive.utils import license_signing

    monkeypatch.setattr(license_signing, "LICENSE_PUBLIC_KEY_B64", public_key_b64)

    dialog = LicenseDialog(database, username="t")
    qtbot.addWidget(dialog)
    dialog._key_input.setPlainText(key)

    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))

    dialog._on_activate_clicked()

    assert "studio rossi" in dialog._status_label.text().lower()
