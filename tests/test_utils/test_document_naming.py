from __future__ import annotations

from datetime import date

from jr_client_archive.domain.client import ClientRead
from jr_client_archive.utils.document_naming import render_document_stem


def _client(**overrides) -> ClientRead:
    base = dict(
        id=1,
        client_code="CLI0001",
        first_name="Mario",
        last_name="Rossi",
        folder_relative_path="CLI0001_ROSSI_MARIO",
        is_active=True,
        created_at="2024-01-01T00:00:00",
        updated_at="2024-01-01T00:00:00",
    )
    base.update(overrides)
    return ClientRead.model_validate(base)


def test_render_document_stem_fills_known_placeholders():
    stem = render_document_stem(
        "{client_code}_{last_name}_{first_name}_{document_type}_{document_date}",
        client=_client(),
        document_type="Fattura",
        category="Contabilita",
        document_date=date(2024, 3, 15),
    )
    assert stem == "CLI0001_ROSSI_MARIO_FATTURA_2024-03-15"


def test_render_document_stem_collapses_blank_placeholders_to_underscore():
    stem = render_document_stem(
        "{client_code}_{document_type}_{document_date}",
        client=_client(),
        document_type=None,
        category=None,
        document_date=None,
    )
    assert stem == "CLI0001"


def test_render_document_stem_ignores_unknown_placeholder():
    stem = render_document_stem(
        "{client_code}_{not_a_real_field}",
        client=_client(),
        document_type=None,
        category=None,
        document_date=None,
    )
    assert stem == "CLI0001"


def test_render_document_stem_falls_back_to_client_code_when_empty():
    stem = render_document_stem(
        "{document_type}",
        client=_client(),
        document_type=None,
        category=None,
        document_date=None,
    )
    assert stem == "CLI0001"
