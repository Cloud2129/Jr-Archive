"""Physical folder operations under the archive root.

Hard rule from the product spec: this service never deletes anything
automatically. It only creates directories, and it always checks for
naming conflicts before doing so - silently overwriting an existing
folder would mean silently losing track of whatever was already in it.
"""

from __future__ import annotations

from pathlib import Path

from jr_client_archive.utils.text import normalize_token


class FilesystemService:
    def __init__(self, archive_root: Path) -> None:
        self._archive_root = archive_root

    def create_client_root_folder(self, desired_name: str) -> str:
        """Create the top-level folder for a new client and return its
        path relative to the archive root. If ``desired_name`` is already
        taken (e.g. two clients sanitizing to the same surname), a numeric
        suffix is appended rather than failing the whole operation.
        """
        relative_path = self._first_available_name(desired_name)
        (self._archive_root / relative_path).mkdir(parents=True, exist_ok=False)
        return relative_path

    def create_subfolder(self, parent_relative_path: str, name: str) -> str:
        """Create a subfolder under an existing folder. Raises
        :class:`FileExistsError` on a name conflict instead of silently
        picking a different name: unlike the client root folder (an
        internal, auto-generated name), a subfolder name is something the
        user just typed and expects to get exactly that name or an error.
        """
        sanitized = normalize_token(name)
        if not sanitized:
            raise ValueError("Nome cartella non valido.")

        relative_path = f"{parent_relative_path}/{sanitized}"
        full_path = self._archive_root / relative_path
        if full_path.exists():
            raise FileExistsError(f"Esiste già una cartella '{sanitized}' in questa posizione.")

        full_path.mkdir(parents=True, exist_ok=False)
        return relative_path

    def _first_available_name(self, desired_name: str) -> str:
        candidate = desired_name
        suffix = 1
        while (self._archive_root / candidate).exists():
            suffix += 1
            candidate = f"{desired_name}_{suffix}"
        return candidate
