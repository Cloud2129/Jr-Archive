"""Lightweight, Qt-free document preview rendering.

Kept free of any PySide6 dependency so it stays unit-testable without a Qt
application and reusable outside the dossier dialog. Only PDF and raster
images are actually rendered to a thumbnail (PyMuPDF / Pillow respectively);
everything else (Office documents, audio, video, ...) is reported as
``UNSUPPORTED`` so the UI falls back to "open with the system's default
application" rather than attempting an unreliable in-app render.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import fitz
from PIL import Image

_PDF_EXTENSIONS = {"pdf"}
_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "bmp", "tiff", "tif", "webp"}
_THUMBNAIL_SIZE = (800, 800)


class PreviewKind(str, Enum):
    IMAGE = "image"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class DocumentPreview:
    kind: PreviewKind
    image_bytes: bytes | None = None


def build_preview(path: Path, extension: str) -> DocumentPreview:
    normalized = extension.lower().lstrip(".")
    if normalized in _PDF_EXTENSIONS:
        return _preview_pdf(path)
    if normalized in _IMAGE_EXTENSIONS:
        return _preview_image(path)
    return DocumentPreview(kind=PreviewKind.UNSUPPORTED)


def _preview_pdf(path: Path) -> DocumentPreview:
    # Corrupted/encrypted/zero-page PDFs must degrade to "no preview"
    # rather than crash the dossier dialog - the user can still open the
    # file externally.
    try:
        with fitz.open(path) as pdf:
            if pdf.page_count == 0:
                return DocumentPreview(kind=PreviewKind.UNSUPPORTED)
            pixmap = pdf.load_page(0).get_pixmap()
            return DocumentPreview(kind=PreviewKind.IMAGE, image_bytes=pixmap.tobytes("png"))
    except Exception:
        return DocumentPreview(kind=PreviewKind.UNSUPPORTED)


def _preview_image(path: Path) -> DocumentPreview:
    try:
        with Image.open(path) as image:
            image = image.convert("RGB")
            image.thumbnail(_THUMBNAIL_SIZE)
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            return DocumentPreview(kind=PreviewKind.IMAGE, image_bytes=buffer.getvalue())
    except Exception:
        return DocumentPreview(kind=PreviewKind.UNSUPPORTED)
