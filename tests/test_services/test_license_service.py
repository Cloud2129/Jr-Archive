from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from jr_client_archive.db.models.license import LicenseStateRow
from jr_client_archive.services.license_service import DEMO_DURATION_DAYS, MAX_DEMO_CLIENTS, LicenseService
from jr_client_archive.utils.license_signing import generate_keypair, sign_license


def test_first_launch_is_recorded_once_and_stays_fixed(database):
    session = database.create_session()
    try:
        first = LicenseService(session).status().first_launch_at
    finally:
        session.close()

    session = database.create_session()
    try:
        second = LicenseService(session).status().first_launch_at
    finally:
        session.close()

    assert first == second


def test_status_within_demo_period_is_not_expired(database):
    session = database.create_session()
    try:
        status = LicenseService(session).status()
    finally:
        session.close()

    assert status.is_demo_expired is False
    assert status.is_read_only is False
    assert status.days_remaining in (DEMO_DURATION_DAYS - 1, DEMO_DURATION_DAYS)
    assert status.is_activated is False


def test_status_after_demo_period_is_expired_and_read_only(database):
    session = database.create_session()
    try:
        LicenseService(session).status()  # initializes the row
        row = session.get(LicenseStateRow, 1)
        row.first_launch_at = datetime.now() - timedelta(days=DEMO_DURATION_DAYS + 1)
        session.commit()
        status = LicenseService(session).status()
    finally:
        session.close()

    assert status.is_demo_expired is True
    assert status.is_read_only is True
    assert status.days_remaining == 0


def test_client_limit_reached_when_not_activated_and_over_limit(database):
    session = database.create_session()
    try:
        status = LicenseService(session).status(active_client_count=MAX_DEMO_CLIENTS)
    finally:
        session.close()

    assert status.client_limit_reached is True


def test_client_limit_not_reached_when_under_limit(database):
    session = database.create_session()
    try:
        status = LicenseService(session).status(active_client_count=MAX_DEMO_CLIENTS - 1)
    finally:
        session.close()

    assert status.client_limit_reached is False


def test_activate_with_valid_key_lifts_restrictions(database, monkeypatch):
    private_key_b64, public_key_b64 = generate_keypair()
    key = sign_license({"licensee": "Studio Rossi"}, private_key_b64=private_key_b64)

    from jr_client_archive.utils import license_signing

    monkeypatch.setattr(license_signing, "LICENSE_PUBLIC_KEY_B64", public_key_b64)

    session = database.create_session()
    try:
        LicenseService(session).status()  # initializes the row with an expired clock below
        row = session.get(LicenseStateRow, 1)
        row.first_launch_at = datetime.now() - timedelta(days=DEMO_DURATION_DAYS + 1)
        session.commit()

        status = LicenseService(session).activate(key)
    finally:
        session.close()

    assert status.is_activated is True
    assert status.licensee == "Studio Rossi"
    assert status.is_read_only is False
    assert status.client_limit_reached is False


def test_activate_with_invalid_key_raises_and_persists_nothing(database):
    session = database.create_session()
    try:
        with pytest.raises(Exception):
            LicenseService(session).activate("not-a-valid-key")
        status = LicenseService(session).status()
    finally:
        session.close()

    assert status.is_activated is False
