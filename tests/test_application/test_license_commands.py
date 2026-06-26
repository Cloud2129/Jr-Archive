from __future__ import annotations

import pytest

from jr_client_archive.application.license_commands import activate_license
from jr_client_archive.application.license_queries import get_license_status
from jr_client_archive.db.models.audit import AuditLogEntry
from jr_client_archive.utils.license_signing import generate_keypair, sign_license


def test_activate_license_records_audit_entry(database, monkeypatch):
    private_key_b64, public_key_b64 = generate_keypair()
    key = sign_license({"licensee": "Studio Rossi"}, private_key_b64=private_key_b64)

    from jr_client_archive.utils import license_signing

    monkeypatch.setattr(license_signing, "LICENSE_PUBLIC_KEY_B64", public_key_b64)

    status = activate_license(database, key, username="alice")

    assert status.is_activated is True
    assert status.licensee == "Studio Rossi"

    session = database.create_session()
    try:
        entries = session.query(AuditLogEntry).filter_by(action="license.activated").all()
        assert len(entries) == 1
        assert entries[0].username == "alice"
        assert "Studio Rossi" in entries[0].details
    finally:
        session.close()

    assert get_license_status(database).is_activated is True


def test_activate_license_with_invalid_key_raises_and_records_nothing(database):
    with pytest.raises(Exception):
        activate_license(database, "not-a-valid-key", username="alice")

    session = database.create_session()
    try:
        entries = session.query(AuditLogEntry).filter_by(action="license.activated").all()
        assert entries == []
    finally:
        session.close()
