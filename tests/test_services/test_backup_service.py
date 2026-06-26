from __future__ import annotations

import zipfile

import pytest

from jr_client_archive.application.client_commands import CreateClientRequest, create_client
from jr_client_archive.application.client_queries import list_clients
from jr_client_archive.config.paths import AppPaths
from jr_client_archive.db.base import Database
from jr_client_archive.domain.client import ClientCreate
from jr_client_archive.services.backup_service import BackupService


def _isolated_paths(tmp_path) -> AppPaths:
    paths = AppPaths(root=tmp_path / "app_home")
    paths.ensure_directories()
    return paths


def test_create_backup_zips_database_and_archive_root(tmp_path):
    paths = _isolated_paths(tmp_path)
    db = Database(tmp_path / "database.sqlite3")
    db.create_all()
    (paths.archive_root / "CLI0001_ROSSI_MARIO").mkdir(parents=True)
    (paths.archive_root / "CLI0001_ROSSI_MARIO" / "fattura.pdf").write_bytes(b"contenuto")

    info = BackupService(paths).create_backup(db)

    assert info.path.exists()
    assert info.path.parent == paths.backups_dir
    with zipfile.ZipFile(info.path) as archive:
        names = archive.namelist()
        assert "database.sqlite3" in names
        assert "Archivio Clienti/CLI0001_ROSSI_MARIO/fattura.pdf" in names

    db.dispose()


def test_list_backups_returns_newest_first(tmp_path):
    paths = _isolated_paths(tmp_path)
    db = Database(tmp_path / "database.sqlite3")
    db.create_all()
    service = BackupService(paths)

    first = service.create_backup(db)
    second = service.create_backup(db)

    backups = service.list_backups()
    assert [backup.path for backup in backups] == [second.path, first.path]
    db.dispose()


def test_list_backups_empty_when_no_backups_exist(tmp_path):
    paths = _isolated_paths(tmp_path)
    assert BackupService(paths).list_backups() == []


def test_restore_moves_current_data_aside_without_deleting_anything(tmp_path):
    paths = _isolated_paths(tmp_path)
    db_path = tmp_path / "database.sqlite3"
    db = Database(db_path)
    db.create_all()
    archive_root = paths.archive_root
    (archive_root / "CLI0001").mkdir(parents=True)
    (archive_root / "CLI0001" / "originale.pdf").write_bytes(b"vecchio")

    service = BackupService(paths)
    backup = service.create_backup(db)

    (archive_root / "CLI0001" / "nuovo.pdf").write_bytes(b"nuovo dopo backup")

    result = service.restore_backup(db, backup.path)

    safety_dir = result.safety_backup_dir
    assert safety_dir.exists()
    assert (safety_dir / db_path.name).exists()
    assert (safety_dir / archive_root.name / "CLI0001" / "originale.pdf").exists()
    assert (safety_dir / archive_root.name / "CLI0001" / "nuovo.pdf").read_bytes() == b"nuovo dopo backup"

    assert (archive_root / "CLI0001" / "originale.pdf").exists()
    assert not (archive_root / "CLI0001" / "nuovo.pdf").exists()
    assert db_path.exists()

    db.dispose()


def test_restore_raises_for_invalid_backup_archive(tmp_path):
    paths = _isolated_paths(tmp_path)
    db = Database(tmp_path / "database.sqlite3")
    db.create_all()

    bogus = paths.backups_dir / "backup_bogus.zip"
    with zipfile.ZipFile(bogus, "w") as archive:
        archive.writestr("not_a_database.txt", "qualcosa")

    try:
        with pytest.raises(ValueError):
            BackupService(paths).restore_backup(db, bogus)
    finally:
        db.dispose()


def test_restore_database_reflects_immediately_without_reopening(app_paths, tmp_path):
    # Uses the app_paths fixture (not a manually built AppPaths) because
    # create_client() resolves folders via the global get_app_paths(),
    # which app_paths redirects under JR_CLIENT_ARCHIVE_HOME for this test.
    db = Database(tmp_path / "database.sqlite3")
    db.create_all()

    create_client(db, CreateClientRequest(client=ClientCreate(first_name="Mario", last_name="Rossi")), username="t")

    service = BackupService(app_paths)
    backup = service.create_backup(db)

    create_client(db, CreateClientRequest(client=ClientCreate(first_name="Luigi", last_name="Verdi")), username="t")
    assert len(list_clients(db)) == 2

    service.restore_backup(db, backup.path)

    clients = list_clients(db)
    assert len(clients) == 1
    assert clients[0].display_name == "Mario Rossi"

    db.dispose()
