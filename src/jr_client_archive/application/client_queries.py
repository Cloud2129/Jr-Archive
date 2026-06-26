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
        clients = ClientRepository(session).list_active()
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


def get_client(database: Database, client_id: int) -> ClientRead | None:
    session = database.create_session()
    try:
        client = ClientRepository(session).get(client_id)
        return ClientRead.model_validate(client) if client else None
    finally:
        session.close()


def count_active_clients(database: Database) -> int:
    session = database.create_session()
    try:
        return ClientRepository(session).count_active()
    finally:
        session.close()
