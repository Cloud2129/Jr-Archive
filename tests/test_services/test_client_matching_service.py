from __future__ import annotations

from jr_client_archive.domain.client import ClientRead
from jr_client_archive.domain.enums import ClientType
from jr_client_archive.services.client_matching_service import match_clients


def _client(**kwargs) -> ClientRead:
    from datetime import datetime

    defaults = dict(
        id=1,
        client_code="CLI0001",
        folder_relative_path="CLI0001_ROSSI_MARIO",
        is_active=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        client_type=ClientType.PERSON,
        first_name="Mario",
        last_name="Rossi",
    )
    defaults.update(kwargs)
    client = ClientRead(**defaults)
    client.display_name = f"{defaults.get('last_name') or ''} {defaults.get('first_name') or ''}".strip()
    if defaults["client_type"] == ClientType.COMPANY:
        client.display_name = defaults.get("company_name") or ""
    return client


def test_exact_match_on_fiscal_code_scores_100():
    client = _client(fiscal_code="RSSMRA80A01H501Z")
    matches = match_clients("RSSMRA80A01H501Z_fattura.pdf", [client])

    assert len(matches) == 1
    assert matches[0].score == 100.0
    assert matches[0].reason == "Codice fiscale"


def test_exact_match_on_client_code():
    client = _client(client_code="CLI0042")
    matches = match_clients("CLI0042_documento.pdf", [client])

    assert matches[0].reason == "Codice cliente"
    assert matches[0].score == 100.0


def test_exact_match_on_vat_number():
    client = _client(vat_number="01234567890")
    matches = match_clients("fattura_01234567890.pdf", [client])

    assert matches[0].reason == "Partita IVA"


def test_exact_match_on_practice_number():
    client = _client(practice_number="PR-2024-007")
    matches = match_clients("PR-2024-007_doc.pdf", [client])

    assert matches[0].reason == "Numero pratica"


def test_fuzzy_match_on_person_name():
    client = _client(first_name="Mario", last_name="Rossi")
    matches = match_clients("rossi_mario_fattura.pdf", [client])

    assert len(matches) == 1
    assert matches[0].reason == "Corrispondenza nome"
    assert matches[0].score >= 55.0


def test_fuzzy_match_on_company_name():
    client = _client(client_type=ClientType.COMPANY, company_name="Acme Costruzioni Srl")
    matches = match_clients("acme_costruzioni_fattura.pdf", [client])

    assert matches[0].reason == "Corrispondenza nome"
    assert matches[0].score >= 55.0


def test_no_match_below_threshold_is_excluded():
    client = _client(first_name="Mario", last_name="Rossi")
    matches = match_clients("completely_unrelated_invoice.pdf", [client])

    assert matches == []


def test_results_sorted_descending_and_capped():
    clients = [
        _client(id=i, client_code=f"CLI000{i}", first_name="Mario", last_name="Rossi")
        for i in range(1, 8)
    ]
    matches = match_clients("rossi_mario.pdf", clients)

    assert len(matches) <= 5
    scores = [m.score for m in matches]
    assert scores == sorted(scores, reverse=True)


def test_exact_signal_wins_over_mediocre_fuzzy_score():
    client = _client(first_name="Mario", last_name="Rossi", client_code="CLI0099")
    matches = match_clients("CLI0099_unrelatedname.pdf", [client])

    assert matches[0].score == 100.0
    assert matches[0].reason == "Codice cliente"
