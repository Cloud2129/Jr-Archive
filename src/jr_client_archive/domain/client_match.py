"""DTO for a candidate client suggested by the drag&drop recognition engine."""

from __future__ import annotations

from pydantic import BaseModel

from jr_client_archive.domain.client import ClientRead


class ClientMatchRead(BaseModel):
    client: ClientRead
    score: float
    reason: str
