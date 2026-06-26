from __future__ import annotations

from jr_client_archive.application.client_commands import CreateClientRequest, create_client
from jr_client_archive.application.client_matching_queries import match_clients_for_filename
from jr_client_archive.domain.client import ClientCreate


def test_match_clients_for_filename_finds_exact_fiscal_code_match(database, app_paths):
    create_client(
        database,
        CreateClientRequest(client=ClientCreate(first_name="Mario", last_name="Rossi", fiscal_code="RSSMRA80A01H501Z")),
        username="t",
    )

    matches = match_clients_for_filename(database, "RSSMRA80A01H501Z_fattura.pdf")

    assert len(matches) == 1
    assert matches[0].client.display_name == "Mario Rossi"
    assert matches[0].reason == "Codice fiscale"


def test_match_clients_for_filename_finds_fuzzy_name_match(database, app_paths):
    create_client(
        database, CreateClientRequest(client=ClientCreate(first_name="Mario", last_name="Rossi")), username="t"
    )

    matches = match_clients_for_filename(database, "rossi_mario_contratto.pdf")

    assert len(matches) == 1
    assert matches[0].reason == "Corrispondenza nome"


def test_match_clients_for_filename_returns_empty_when_no_clients(database, app_paths):
    matches = match_clients_for_filename(database, "qualunque_documento.pdf")

    assert matches == []
