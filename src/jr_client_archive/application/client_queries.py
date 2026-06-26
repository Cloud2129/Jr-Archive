"""Read-only client use cases consumed by the UI.

The UI never imports ``repositories`` or ``db.models`` directly - it calls
through here and only ever sees :class:`ClientRead` DTOs. Each function
owns its own short-lived session (open, query, close) rather than holding
one open for the lifetime of a widget.
"""

from __future__ import annotations

from jr_client_archive.db.base import Database
from jr_client_archive.domain.client import ClientRead
from jr_client_archive.repositories.client_repository import ClientRepository


def list_clients(database: Database) -> list[ClientRead]:
    session = database.create_session()
    try:
        clients = ClientRepository(session).list_all()
        return [ClientRead.model_validate(client) for client in clients]
    finally:
        session.close()


def search_clients(database: Database, term: str) -> list[ClientRead]:
    if not term.strip():
        return list_clients(database)
    session = database.create_session()
    try:
        clients = ClientRepository(session).search(term.strip())
        return [ClientRead.model_validate(client) for client in clients]
    finally:
        session.close()
