from __future__ import annotations

from sqlalchemy import func, select

from jr_client_archive.db.models.client import Client
from jr_client_archive.repositories.base import BaseRepository


class ClientRepository(BaseRepository[Client]):
    model = Client

    def get_by_code(self, client_code: str) -> Client | None:
        return self._session.scalar(select(Client).where(Client.client_code == client_code))

    def list_active(self) -> list[Client]:
        return list(
            self._session.scalars(
                select(Client).where(Client.is_active.is_(True)).order_by(Client.last_name, Client.company_name)
            )
        )

    def count_active(self) -> int:
        return self._session.scalar(
            select(func.count()).select_from(Client).where(Client.is_active.is_(True))
        )

    def search(self, term: str) -> list[Client]:
        """Instant search across the fields a user would actually type.

        A simple ``LIKE`` is enough up to the documented scale (150
        clients): the table is tiny, every relevant column is indexed, and
        SQLite will happily scan it in well under a millisecond. This is
        intentionally not FTS5 - that's reserved for the much larger
        document corpus in the global search phase.
        """
        pattern = f"%{term}%"
        return list(
            self._session.scalars(
                select(Client).where(
                    Client.is_active.is_(True),
                    (Client.first_name.ilike(pattern))
                    | (Client.last_name.ilike(pattern))
                    | (Client.company_name.ilike(pattern))
                    | (Client.client_code.ilike(pattern))
                    | (Client.fiscal_code.ilike(pattern))
                    | (Client.vat_number.ilike(pattern))
                    | (Client.practice_number.ilike(pattern)),
                )
            )
        )

    def next_client_code(self, prefix: str = "CLI") -> str:
        """Generate the next sequential client code (e.g. CLI0001, CLI0002).

        Derives the number from the count of existing codes with this
        prefix rather than a separate counter table, so it self-heals if a
        client is ever deleted.
        """
        existing = self._session.scalars(
            select(Client.client_code).where(Client.client_code.like(f"{prefix}%"))
        ).all()
        max_seq = 0
        for code in existing:
            suffix = code[len(prefix):]
            if suffix.isdigit():
                max_seq = max(max_seq, int(suffix))
        return f"{prefix}{max_seq + 1:04d}"
