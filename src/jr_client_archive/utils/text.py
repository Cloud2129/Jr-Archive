"""Filesystem-safe text normalization.

Used everywhere a user-provided string (a client's surname, a folder name
typed by hand) needs to become part of a path. Centralized so the rule for
"what is a valid folder/file name component" is defined exactly once.
"""

from __future__ import annotations

import re
import unicodedata

_INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_WHITESPACE = re.compile(r"\s+")


def normalize_token(value: str) -> str:
    """Strip accents/diacritics, remove characters illegal in a path
    component on any major OS, collapse whitespace to underscores, and
    uppercase the result (matches the naming convention used throughout
    the app, e.g. ``CLI0001_ROSSI_MARIO``).
    """
    decomposed = unicodedata.normalize("NFKD", value)
    without_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    cleaned = _INVALID_CHARS.sub("", without_accents)
    return _WHITESPACE.sub("_", cleaned.strip()).upper()


def build_folder_name(*parts: str | None) -> str:
    """Join non-empty parts into a single sanitized folder name."""
    tokens = [normalize_token(part) for part in parts if part]
    return "_".join(token for token in tokens if token)
