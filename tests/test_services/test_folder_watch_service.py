from __future__ import annotations

import threading
import time

from jr_client_archive.services.folder_watch_service import FolderWatchService


def _wait_for(event: threading.Event, timeout: float = 5.0) -> None:
    assert event.wait(timeout), "il watcher non ha rilevato la modifica entro il timeout"


def test_detects_file_rename_within_same_directory(tmp_path):
    archive_root = tmp_path / "archivio"
    folder = archive_root / "cliente"
    folder.mkdir(parents=True)
    source = folder / "originale.pdf"
    source.write_bytes(b"contenuto")

    received = {}
    event = threading.Event()

    def callback(old_relative, new_relative, is_directory):
        received["old"] = old_relative
        received["new"] = new_relative
        received["is_directory"] = is_directory
        event.set()

    service = FolderWatchService(archive_root, callback)
    service.start()
    try:
        time.sleep(0.2)  # lascia che l'observer si avvii prima di agire sul filesystem
        source.rename(folder / "rinominato.pdf")
        _wait_for(event)
    finally:
        service.stop()

    assert received["old"] == "cliente/originale.pdf"
    assert received["new"] == "cliente/rinominato.pdf"
    assert received["is_directory"] is False


def test_detects_directory_move(tmp_path):
    archive_root = tmp_path / "archivio"
    folder = archive_root / "cliente" / "vecchia_cartella"
    folder.mkdir(parents=True)

    received = {}
    event = threading.Event()

    def callback(old_relative, new_relative, is_directory):
        received["old"] = old_relative
        received["new"] = new_relative
        received["is_directory"] = is_directory
        event.set()

    service = FolderWatchService(archive_root, callback)
    service.start()
    try:
        time.sleep(0.2)
        folder.rename(archive_root / "cliente" / "nuova_cartella")
        _wait_for(event)
    finally:
        service.stop()

    assert received["old"] == "cliente/vecchia_cartella"
    assert received["new"] == "cliente/nuova_cartella"
    assert received["is_directory"] is True
