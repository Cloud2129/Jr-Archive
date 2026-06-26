from __future__ import annotations

from jr_client_archive.application.client_commands import CreateClientRequest, create_client
from jr_client_archive.application.document_commands import add_document
from jr_client_archive.application.folder_queries import list_folders_for_client
from jr_client_archive.application.global_search_queries import global_search
from jr_client_archive.domain.client import ClientCreate


def _create_client(database, first_name, last_name):
    return create_client(
        database,
        CreateClientRequest(client=ClientCreate(first_name=first_name, last_name=last_name)),
        username="t",
    )


def test_global_search_returns_matching_clients_and_documents(database, app_paths, tmp_path):
    rossi = _create_client(database, "Mario", "Rossi")
    _create_client(database, "Giulia", "Bianchi")
    folder = list_folders_for_client(database, rossi.id)[0]
    source = tmp_path / "fattura_rossi.pdf"
    source.write_bytes(b"contenuto")
    add_document(database, rossi.id, folder.id, source, username="t")

    result = global_search(database, "rossi")

    assert [c.display_name for c in result.clients] == ["Mario Rossi"]
    assert [d.original_filename for d in result.documents] == ["fattura_rossi.pdf"]


def test_global_search_blank_term_returns_empty_result(database, app_paths):
    _create_client(database, "Mario", "Rossi")

    result = global_search(database, "   ")

    assert result.clients == []
    assert result.documents == []


def test_global_search_caps_results(database, app_paths, tmp_path, monkeypatch):
    import jr_client_archive.application.global_search_queries as module

    monkeypatch.setattr(module, "_MAX_CLIENT_RESULTS", 1)
    monkeypatch.setattr(module, "_MAX_DOCUMENT_RESULTS", 1)

    rossi = _create_client(database, "Mario", "Rossi")
    _create_client(database, "Paolo", "Rossini")
    folder = list_folders_for_client(database, rossi.id)[0]
    for name in ("rossi_a.pdf", "rossi_b.pdf"):
        source = tmp_path / name
        source.write_bytes(b"contenuto")
        add_document(database, rossi.id, folder.id, source, username="t")

    result = global_search(database, "rossi")

    assert len(result.clients) == 1
    assert len(result.documents) == 1
