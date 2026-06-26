"""Pydantic DTOs for the Client entity.

These are what the application/service layer and the UI exchange - never
the SQLAlchemy ORM object itself. Keeping the two separate means a future
change to the persistence model (e.g. switching an ORM relationship) can't
silently leak into the UI layer, and pydantic gives us validation for free
on every boundary crossing.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from jr_client_archive.domain.enums import ClientType


class ClientBase(BaseModel):
    client_type: ClientType = ClientType.PERSON
    first_name: str | None = None
    last_name: str | None = None
    company_name: str | None = None
    fiscal_code: str | None = None
    vat_number: str | None = None
    practice_number: str | None = None
    email: str | None = None
    phone: str | None = None
    notes: str | None = None


class ClientCreate(ClientBase):
    """Data required to create a new client.

    ``client_code`` and ``folder_relative_path`` are deliberately absent:
    they are derived/assigned by ``ClientService``, never supplied by the
    caller, so there is exactly one place that can produce them.
    """


class ClientUpdate(BaseModel):
    client_type: ClientType | None = None
    first_name: str | None = None
    last_name: str | None = None
    company_name: str | None = None
    fiscal_code: str | None = None
    vat_number: str | None = None
    practice_number: str | None = None
    email: str | None = None
    phone: str | None = None
    notes: str | None = None
    is_active: bool | None = None


class ClientRead(ClientBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_code: str
    folder_relative_path: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    display_name: str = Field(default="")
