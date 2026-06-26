from __future__ import annotations

import io

import fitz
import pytest
from PIL import Image

from jr_client_archive.services.document_preview_service import PreviewKind, build_preview


@pytest.fixture
def pdf_path(tmp_path):
    path = tmp_path / "documento.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "ciao")
    doc.save(path)
    doc.close()
    return path


@pytest.fixture
def image_path(tmp_path):
    path = tmp_path / "foto.png"
    Image.new("RGB", (1200, 900), color="blue").save(path)
    return path


def test_build_preview_renders_pdf_first_page(pdf_path):
    preview = build_preview(pdf_path, "pdf")

    assert preview.kind == PreviewKind.IMAGE
    assert preview.image_bytes
    rendered = Image.open(io.BytesIO(preview.image_bytes))
    assert rendered.format == "PNG"


def test_build_preview_renders_and_thumbnails_image(image_path):
    preview = build_preview(image_path, "png")

    assert preview.kind == PreviewKind.IMAGE
    rendered = Image.open(io.BytesIO(preview.image_bytes))
    assert rendered.width <= 800
    assert rendered.height <= 800


def test_build_preview_handles_extension_with_leading_dot(image_path):
    preview = build_preview(image_path, ".PNG")

    assert preview.kind == PreviewKind.IMAGE


def test_build_preview_unsupported_for_office_extension(tmp_path):
    path = tmp_path / "contratto.docx"
    path.write_bytes(b"not a real docx")

    preview = build_preview(path, "docx")

    assert preview.kind == PreviewKind.UNSUPPORTED
    assert preview.image_bytes is None


def test_build_preview_degrades_gracefully_on_corrupted_pdf(tmp_path):
    path = tmp_path / "corrotto.pdf"
    path.write_bytes(b"not a real pdf")

    preview = build_preview(path, "pdf")

    assert preview.kind == PreviewKind.UNSUPPORTED


def test_build_preview_unsupported_for_video_and_audio(tmp_path):
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"fake video")
    audio = tmp_path / "nota.mp3"
    audio.write_bytes(b"fake audio")

    assert build_preview(video, "mp4").kind == PreviewKind.UNSUPPORTED
    assert build_preview(audio, "mp3").kind == PreviewKind.UNSUPPORTED
