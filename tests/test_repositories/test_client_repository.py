from __future__ import annotations

from jr_client_archive.db.models.client import Client
from jr_client_archive.domain.enums import ClientType
from jr_client_archive.repositories.client_repository import ClientRepository


def _make_client(repo: ClientRepository, **overrides) -> Client:
    code = overrides.pop("client_code", None) or repo.next_client_code()
    defaults = dict(
        client_code=code,
        client_type=ClientType.PERSON,
        first_name="Mario",
        last_name="Rossi",
        folder_relative_path=f"{code}_ROSSI_MARIO",
    )
    defaults.update(overrides)
    return repo.add(Client(**defaults))


def test_next_client_code_is_sequential(database):
    session = database.create_session()
    repo = ClientRepository(session)

    assert repo.next_client_code() == "CLI0001"
    _make_client(repo)
    assert repo.next_client_code() == "CLI0002"


def test_get_by_code_roundtrip(database):
    session = database.create_session()
    repo = ClientRepository(session)
    created = _make_client(repo)
    session.commit()

    found = repo.get_by_code(created.client_code)
    assert found is not None
    assert found.id == created.id
    assert found.display_name == "Mario Rossi"


def test_search_matches_name_code_and_fiscal_code(database):
    session = database.create_session()
    repo = ClientRepository(session)
    _make_client(repo, first_name="Mario", last_name="Rossi", fiscal_code="RSSMRA80A01H501Z")
    _make_client(repo, first_name="Luigi", last_name="Verdi", fiscal_code="VRDLGU80A01H501Z")
    session.commit()

    assert {c.last_name for c in repo.search("rossi")} == {"Rossi"}
    assert {c.last_name for c in repo.search("CLI0002")} == {"Verdi"}
    assert {c.last_name for c in repo.search("RSSMRA80A01H501Z")} == {"Rossi"}
    assert repo.search("nessuno") == []
