"""Generic repository base class.

Every concrete repository (ClientRepository, DocumentRepository, ...) gets
basic get/list/add/delete for free and only adds the queries that are
actually specific to its entity. The session is injected, never created
here - this class has no opinion about transactions or commit boundaries,
that belongs to the service layer above it.
"""

from __future__ import annotations

from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, entity_id: int) -> ModelT | None:
        return self._session.get(self.model, entity_id)

    def list_all(self) -> list[ModelT]:
        return list(self._session.scalars(select(self.model)))

    def add(self, entity: ModelT) -> ModelT:
        self._session.add(entity)
        self._session.flush()
        return entity

    def delete(self, entity: ModelT) -> None:
        self._session.delete(entity)
        self._session.flush()
