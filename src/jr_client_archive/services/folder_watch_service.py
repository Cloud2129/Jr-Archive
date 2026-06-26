"""Watches the archive root for files/folders renamed or moved outside the app.

Deliberately reacts only to *moves* (which `watchdog` reports for renames
too, since a rename is just a move within the same directory). Creations
and deletions are out of scope on purpose:

- a new file appearing on disk belongs to the explicit drag&drop/upload
  ingestion flow, not to silent auto-ingestion;
- a file disappearing must never cascade into deleting its database record
  - "mai cancellare automaticamente file" - so doing nothing is the correct,
  safe behaviour there.

A rename/move, however, would otherwise leave the stored ``relative_path``
pointing at something that no longer exists on disk, silently breaking
preview/open and desynchronizing the folder tree from reality - that one
case is worth reconciling automatically.

This module has no Qt and no database dependency: it only translates raw
filesystem events into ``(old_relative_path, new_relative_path,
is_directory)`` tuples passed to a plain callback. The caller (the main
window) is responsible for hopping back onto the Qt main thread - the
watchdog observer runs its handler on its own background thread, and
neither Qt widgets nor SQLAlchemy sessions in this codebase are touched
from anywhere but the main thread.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

MovedCallback = Callable[[str, str, bool], None]


class _MovedEventHandler(FileSystemEventHandler):
    def __init__(self, archive_root: Path, callback: MovedCallback) -> None:
        self._archive_root = archive_root
        self._callback = callback

    def on_moved(self, event) -> None:
        try:
            old_relative = Path(event.src_path).relative_to(self._archive_root).as_posix()
            new_relative = Path(event.dest_path).relative_to(self._archive_root).as_posix()
        except ValueError:
            return
        self._callback(old_relative, new_relative, event.is_directory)


class FolderWatchService:
    """Thin, start/stop wrapper around a watchdog ``Observer`` scoped to
    ``archive_root``. Not started automatically: the caller decides when a
    live filesystem watcher is appropriate (e.g. never in tests).
    """

    def __init__(self, archive_root: Path, callback: MovedCallback) -> None:
        self._observer = Observer()
        self._observer.schedule(_MovedEventHandler(archive_root, callback), str(archive_root), recursive=True)

    def start(self) -> None:
        self._observer.start()

    def stop(self) -> None:
        self._observer.stop()
        self._observer.join()
