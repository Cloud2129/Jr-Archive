from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from jr_client_archive.db.base import Base


class AuditLogEntry(Base):
    """Global, queryable business audit trail.

    Every access, modification, rename, error, backup and import is
    expected to write one row here (see ``services.audit_service``). This
    is intentionally append-only and has no foreign keys: it must never
    fail to record an event just because the entity it refers to was later
    deleted.
    """

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    username: Mapped[str] = mapped_column(String(128))
    action: Mapped[str] = mapped_column(String(128), index=True)
    entity_type: Mapped[str | None] = mapped_column(String(64))
    entity_id: Mapped[int | None] = mapped_column(Integer)
    details: Mapped[str | None] = mapped_column(Text)
