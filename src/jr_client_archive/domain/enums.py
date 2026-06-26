"""Business vocabulary shared by every layer.

These enums are the single source of truth: the ORM models (``db.models``)
and the pydantic DTOs (``domain.*``) both import from here instead of each
defining their own copy, so the two can never drift apart.
"""

from __future__ import annotations

import enum


class ClientType(str, enum.Enum):
    PERSON = "PERSON"
    COMPANY = "COMPANY"


class EntityType(str, enum.Enum):
    """Which kind of record a custom field (or its value) belongs to."""

    CLIENT = "CLIENT"
    DOCUMENT = "DOCUMENT"


class CustomFieldType(str, enum.Enum):
    TEXT = "TEXT"
    NUMBER = "NUMBER"
    DATE = "DATE"
    BOOLEAN = "BOOLEAN"
    CHOICE = "CHOICE"


class DocumentStatus(str, enum.Enum):
    TO_VERIFY = "TO_VERIFY"
    CATALOGUED = "CATALOGUED"


class HistoryEventType(str, enum.Enum):
    CREATED = "CREATED"
    RENAMED = "RENAMED"
    MOVED = "MOVED"
    MODIFIED = "MODIFIED"
    CATALOGUED = "CATALOGUED"
