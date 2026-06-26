"""Physical folder operations under the archive root.

Hard rule from the product spec: this service never deletes anything
automatically. It only creates directories, and it always checks for
naming conflicts before doing so - silently overwriting an existing
folder would mean silently losing track of whatever was already in it.
"""

from __future__ import annotations

import shutil
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

    def copy_document_into_folder(
        self, source_path: Path, folder_relative_path: str, desired_stem: str, extension: str
    ) -> str:
        """Copies a document into an existing folder, never the original.

        The source file is left untouched on purpose: ingesting a document
        must never look like deleting/moving something from wherever the
        user dragged it from. A name conflict (two documents that would
        sanitize to the same stem) gets a numeric suffix rather than
        overwriting whatever is already there.
        """
        target_dir = self._archive_root / folder_relative_path
        desired_filename = f"{desired_stem}.{extension}" if extension else desired_stem
        final_filename = self._first_available_filename(target_dir, desired_filename)
        target_path = target_dir / final_filename
        shutil.copy2(source_path, target_path)
        return f"{folder_relative_path}/{final_filename}"

    def rename_document(self, relative_path: str, new_stem: str) -> str:
        """Renames a document in place (same folder), checking for
        conflicts first. Returns the path unchanged if the computed name
        already matches - so callers can tell "renamed" from "no-op" by
        comparing the result to the input.
        """
        current_path = self._archive_root / relative_path
        extension = current_path.suffix.lstrip(".")
        desired_filename = f"{new_stem}.{extension}" if extension else new_stem
        if current_path.name == desired_filename:
            return relative_path

        final_filename = self._first_available_filename(current_path.parent, desired_filename)
        target_path = current_path.parent / final_filename
        current_path.rename(target_path)

        parent_relative = str(Path(relative_path).parent)
        return f"{parent_relative}/{final_filename}" if parent_relative != "." else final_filename

    def _first_available_name(self, desired_name: str) -> str:
        candidate = desired_name
        suffix = 1
        while (self._archive_root / candidate).exists():
            suffix += 1
            candidate = f"{desired_name}_{suffix}"
        return candidate

    def _first_available_filename(self, directory: Path, desired_filename: str) -> str:
        candidate_path = directory / desired_filename
        if not candidate_path.exists():
            return desired_filename

        stem, suffix = candidate_path.stem, candidate_path.suffix
        counter = 2
        while True:
            candidate = f"{stem}_{counter}{suffix}"
            if not (directory / candidate).exists():
                return candidate
            counter += 1
