from __future__ import annotations

from jr_client_archive.services.filesystem_service import FilesystemService


def test_copy_document_into_folder_preserves_source(tmp_path):
    archive_root = tmp_path / "archive"
    folder = archive_root / "CLI0001_ROSSI_MARIO"
    folder.mkdir(parents=True)
    source = tmp_path / "incoming" / "fattura.pdf"
    source.parent.mkdir()
    source.write_bytes(b"contenuto originale")

    service = FilesystemService(archive_root)
    relative_path = service.copy_document_into_folder(source, "CLI0001_ROSSI_MARIO", "fattura", "pdf")

    assert relative_path == "CLI0001_ROSSI_MARIO/fattura.pdf"
    assert (archive_root / relative_path).read_bytes() == b"contenuto originale"
    assert source.exists()
    assert source.read_bytes() == b"contenuto originale"


def test_copy_document_into_folder_suffixes_on_conflict(tmp_path):
    archive_root = tmp_path / "archive"
    folder = archive_root / "CLI0001_ROSSI_MARIO"
    folder.mkdir(parents=True)
    (folder / "fattura.pdf").write_bytes(b"esistente")
    source = tmp_path / "fattura.pdf"
    source.write_bytes(b"nuovo")

    service = FilesystemService(archive_root)
    relative_path = service.copy_document_into_folder(source, "CLI0001_ROSSI_MARIO", "fattura", "pdf")

    assert relative_path == "CLI0001_ROSSI_MARIO/fattura_2.pdf"
    assert (archive_root / "CLI0001_ROSSI_MARIO" / "fattura.pdf").read_bytes() == b"esistente"
    assert (archive_root / relative_path).read_bytes() == b"nuovo"


def test_rename_document_renames_in_place(tmp_path):
    archive_root = tmp_path / "archive"
    folder = archive_root / "CLI0001_ROSSI_MARIO"
    folder.mkdir(parents=True)
    (folder / "fattura.pdf").write_bytes(b"contenuto")

    service = FilesystemService(archive_root)
    new_relative_path = service.rename_document("CLI0001_ROSSI_MARIO/fattura.pdf", "CLI0001_ROSSI_FATTURA_2024-01-01")

    assert new_relative_path == "CLI0001_ROSSI_MARIO/CLI0001_ROSSI_FATTURA_2024-01-01.pdf"
    assert (archive_root / new_relative_path).exists()
    assert not (folder / "fattura.pdf").exists()


def test_rename_document_is_noop_when_name_unchanged(tmp_path):
    archive_root = tmp_path / "archive"
    folder = archive_root / "CLI0001_ROSSI_MARIO"
    folder.mkdir(parents=True)
    (folder / "fattura.pdf").write_bytes(b"contenuto")

    service = FilesystemService(archive_root)
    relative_path = service.rename_document("CLI0001_ROSSI_MARIO/fattura.pdf", "fattura")

    assert relative_path == "CLI0001_ROSSI_MARIO/fattura.pdf"


def test_rename_document_suffixes_on_conflict(tmp_path):
    archive_root = tmp_path / "archive"
    folder = archive_root / "CLI0001_ROSSI_MARIO"
    folder.mkdir(parents=True)
    (folder / "fattura.pdf").write_bytes(b"contenuto A")
    (folder / "nuovo_nome.pdf").write_bytes(b"contenuto B")

    service = FilesystemService(archive_root)
    new_relative_path = service.rename_document("CLI0001_ROSSI_MARIO/fattura.pdf", "nuovo_nome")

    assert new_relative_path == "CLI0001_ROSSI_MARIO/nuovo_nome_2.pdf"
    assert (archive_root / "CLI0001_ROSSI_MARIO" / "nuovo_nome.pdf").read_bytes() == b"contenuto B"
    assert (archive_root / new_relative_path).read_bytes() == b"contenuto A"
