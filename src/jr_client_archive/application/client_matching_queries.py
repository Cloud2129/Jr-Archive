"""Read-only use case behind the drag&drop client-recognition engine."""

from __future__ import annotations

from jr_client_archive.db.base import Database
from jr_client_archive.domain.client import ClientRead
from jr_client_archive.domain.client_match import ClientMatchRead
from jr_client_archive.repositories.client_repository import ClientRepository
from jr_client_archive.services.client_matching_service import match_clients


def match_clients_for_filename(database: Database, filename: str) -> list[ClientMatchRead]:
    session = database.create_session()
    try:
        clients = [ClientRead.model_validate(client) for client in ClientRepository(session).list_active()]
        return match_clients(filename, clients)
    finally:
        session.close()
