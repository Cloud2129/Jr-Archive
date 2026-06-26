from __future__ import annotations

from pydantic import BaseModel, Field

from jr_client_archive.domain.client import ClientRead
from jr_client_archive.domain.document import DocumentRead


class GlobalSearchResult(BaseModel):
    clients: list[ClientRead] = Field(default_factory=list)
    documents: list[DocumentRead] = Field(default_factory=list)
