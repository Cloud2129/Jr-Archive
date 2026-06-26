from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, Date, DateTime, Enum, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from jr_client_archive.db.base import Base
from jr_client_archive.db.models.mixins import TimestampMixin
from jr_client_archive.domain.enums import DocumentStatus, HistoryEventType

if TYPE_CHECKING:
    from jr_client_archive.db.models.client import Client
    from jr_client_archive.db.models.folder import Folder


document_tags = Table(
    "document_tags",
    Base.metadata,
    Column("document_id", ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(TimestampMixin, Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)

    documents: Mapped[list["Document"]] = relationship(
        secondary=document_tags, back_populates="tags"
    )


class Document(TimestampMixin, Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)

    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), index=True
    )
    folder_id: Mapped[int] = mapped_column(
        ForeignKey("folders.id", ondelete="CASCADE"), index=True
    )

    original_filename: Mapped[str] = mapped_column(String(512))
    stored_filename: Mapped[str] = mapped_column(String(512))

    # Relative to AppPaths.archive_root - the single source of truth used
    # to detect external renames/moves via the watchdog sync service.
    relative_path: Mapped[str] = mapped_column(String(1024), unique=True)

    extension: Mapped[str] = mapped_column(String(16), index=True)
    size_bytes: Mapped[int] = mapped_column(Integer)
    checksum_sha256: Mapped[str] = mapped_column(String(64), index=True)

    document_type: Mapped[str | None] = mapped_column(String(128))
    category: Mapped[str | None] = mapped_column(String(128), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    document_date: Mapped[date | None] = mapped_column(Date)

    uploaded_at: Mapped[datetime] = mapped_column(DateTime)
    uploaded_by: Mapped[str | None] = mapped_column(String(128))

    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus), default=DocumentStatus.TO_VERIFY, nullable=False, index=True
    )

    client: Mapped["Client"] = relationship(back_populates="documents")
    folder: Mapped["Folder"] = relationship(back_populates="documents")
    tags: Mapped[list["Tag"]] = relationship(secondary=document_tags, back_populates="documents")
    history: Mapped[list["DocumentHistoryEntry"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="DocumentHistoryEntry.occurred_at"
    )


class DocumentHistoryEntry(Base):
    """Append-only audit trail of what happened to a single document.

    Kept separate from the generic ``audit_log`` table: this one is scoped
    to a document and is what the "cronologia" tab in the UI renders
    directly, without filtering a global log.
    """

    __tablename__ = "document_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )

    event_type: Mapped[HistoryEventType] = mapped_column(Enum(HistoryEventType))
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    performed_by: Mapped[str | None] = mapped_column(String(128))
    occurred_at: Mapped[datetime] = mapped_column(DateTime)

    document: Mapped["Document"] = relationship(back_populates="history")
