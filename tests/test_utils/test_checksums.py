from __future__ import annotations

import hashlib

from jr_client_archive.utils.checksums import sha256_file


def test_sha256_file_matches_hashlib(tmp_path):
    path = tmp_path / "doc.txt"
    path.write_bytes(b"contenuto di prova" * 1000)

    expected = hashlib.sha256(path.read_bytes()).hexdigest()
    assert sha256_file(path) == expected


def test_sha256_file_empty_file(tmp_path):
    path = tmp_path / "empty.txt"
    path.write_bytes(b"")

    assert sha256_file(path) == hashlib.sha256(b"").hexdigest()
