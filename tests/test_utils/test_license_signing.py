from __future__ import annotations

import pytest

from jr_client_archive.utils.license_signing import (
    InvalidLicenseKeyError,
    generate_keypair,
    sign_license,
    verify_license,
)


def test_sign_and_verify_round_trip():
    private_key_b64, public_key_b64 = generate_keypair()
    key = sign_license({"licensee": "Studio Rossi"}, private_key_b64=private_key_b64)

    payload = verify_license(key, public_key_b64=public_key_b64)

    assert payload == {"licensee": "Studio Rossi"}


def test_verify_rejects_key_signed_by_a_different_keypair():
    private_key_b64, _ = generate_keypair()
    _, other_public_key_b64 = generate_keypair()
    key = sign_license({"licensee": "Studio Rossi"}, private_key_b64=private_key_b64)

    with pytest.raises(InvalidLicenseKeyError):
        verify_license(key, public_key_b64=other_public_key_b64)


def test_verify_rejects_tampered_payload():
    private_key_b64, public_key_b64 = generate_keypair()
    key = sign_license({"licensee": "Studio Rossi"}, private_key_b64=private_key_b64)
    prefix, payload_b64, signature_b64 = key.split(".")
    tampered = f"{prefix}.{payload_b64}x.{signature_b64}"

    with pytest.raises(InvalidLicenseKeyError):
        verify_license(tampered, public_key_b64=public_key_b64)


@pytest.mark.parametrize("garbage", ["", "not-a-key", "JRSL1.onlyonepart", "WRONG.aaaa.bbbb"])
def test_verify_rejects_malformed_keys(garbage):
    with pytest.raises(InvalidLicenseKeyError):
        verify_license(garbage)
