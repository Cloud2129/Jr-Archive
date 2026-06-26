#!/usr/bin/env python
"""Offline dev tool: signs a license key with the production private key.

Never run this on a machine that ships to a customer - the private key
must stay only on the developer's side, never inside the application or
the repository. The running app embeds and uses only the matching public
key (see ``jr_client_archive.utils.license_signing.LICENSE_PUBLIC_KEY_B64``).

Usage:
    python scripts/generate_license.py --private-key <base64url-key> --licensee "Studio Rossi"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from jr_client_archive.utils.license_signing import sign_license


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-key", required=True, help="Base64url-encoded Ed25519 private key")
    parser.add_argument("--licensee", required=True, help="Name to embed in the license payload")
    args = parser.parse_args()

    license_key = sign_license({"licensee": args.licensee}, private_key_b64=args.private_key)
    print(license_key)


if __name__ == "__main__":
    main()
