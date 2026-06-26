"""Offline license key signing/verification (Ed25519).

The application never talks to an activation server - per the "mai cloud"
rule, it cannot. Instead, a license key is a small JSON payload signed with
an Ed25519 private key kept offline by JR Solutions; the app ships only the
matching *public* key (``LICENSE_PUBLIC_KEY_B64`` below) and can therefore
verify a key's authenticity without ever needing to reach out anywhere.
``generate_keypair``/``sign_license`` are used by the separate, unshipped
``scripts/generate_license.py`` tool to issue keys - the running application
only ever calls ``verify_license``.
"""

from __future__ import annotations

import base64
import json

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

_KEY_PREFIX = "JRSL1"

# Public half of the production signing keypair. The private half is kept
# offline by JR Solutions and is never part of this repository.
LICENSE_PUBLIC_KEY_B64 = "AvnWqm1DXoQ3ToOCUqIgpqeOxeZ1XzSeiEuwa1TbpMo"


class InvalidLicenseKeyError(ValueError):
    pass


def generate_keypair() -> tuple[str, str]:
    """Returns ``(private_key_b64, public_key_b64)`` for a fresh signing
    keypair. Offline dev tool only - never called by the running app."""
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    return (
        _b64_encode(private_key.private_bytes_raw()),
        _b64_encode(public_key.public_bytes_raw()),
    )


def sign_license(payload: dict, *, private_key_b64: str) -> str:
    """Signs ``payload`` and returns the license key string to hand to a
    customer. Offline dev tool only - never called by the running app."""
    private_key = Ed25519PrivateKey.from_private_bytes(_b64_decode(private_key_b64))
    payload_bytes = _encode_payload(payload)
    signature = private_key.sign(payload_bytes)
    return f"{_KEY_PREFIX}.{_b64_encode(payload_bytes)}.{_b64_encode(signature)}"


def verify_license(license_key: str, *, public_key_b64: str | None = None) -> dict:
    """Verifies a license key against the embedded public key (or
    ``public_key_b64`` when explicitly overridden, e.g. by tests) and
    returns its payload. Raises :class:`InvalidLicenseKeyError` if the key
    is malformed, tampered with, or signed by a different keypair."""
    parts = license_key.strip().split(".")
    if len(parts) != 3 or parts[0] != _KEY_PREFIX:
        raise InvalidLicenseKeyError("Formato della chiave di licenza non valido.")
    _prefix, payload_b64, signature_b64 = parts

    try:
        payload_bytes = _b64_decode(payload_b64)
        signature = _b64_decode(signature_b64)
        public_key = Ed25519PublicKey.from_public_bytes(
            _b64_decode(public_key_b64 if public_key_b64 is not None else LICENSE_PUBLIC_KEY_B64)
        )
        public_key.verify(signature, payload_bytes)
    except (InvalidSignature, ValueError) as exc:
        raise InvalidLicenseKeyError("Chiave di licenza non valida.") from exc

    return json.loads(payload_bytes)


def _encode_payload(payload: dict) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64_decode(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))
