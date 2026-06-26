from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from jr_client_archive.db.base import Base
from jr_client_archive.db.models.mixins import TimestampMixin
from jr_client_archive.domain.enums import ClientType

if TYPE_CHECKING:
    from jr_client_archive.db.models.document import Document
    from jr_client_archive.db.models.folder import Folder


class Client(TimestampMixin, Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)

    client_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    client_type: Mapped[ClientType] = mapped_column(
        Enum(ClientType), default=ClientType.PERSON, nullable=False
    )

    first_name: Mapped[str | None] = mapped_column(String(128))
    last_name: Mapped[str | None] = mapped_column(String(128))
    company_name: Mapped[str | None] = mapped_column(String(256))

    fiscal_code: Mapped[str | None] = mapped_column(String(32), index=True)
    vat_number: Mapped[str | None] = mapped_column(String(32), index=True)
    practice_number: Mapped[str | None] = mapped_column(String(64), index=True)

    email: Mapped[str | None] = mapped_column(String(256))
    phone: Mapped[str | None] = mapped_column(String(64))

    # Relative to AppPaths.archive_root - never an absolute path, so the
    # whole archive can be relocated/restored to a different machine/drive.
    folder_relative_path: Mapped[str] = mapped_column(String(512), unique=True)

    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    folders: Mapped[list["Folder"]] = relationship(
        back_populates="client", cascade="all, delete-orphan"
    )
    documents: Mapped[list["Document"]] = relationship(
        back_populates="client", cascade="all, delete-orphan"
    )

    @property
    def display_name(self) -> str:
        if self.client_type is ClientType.COMPANY and self.company_name:
            return self.company_name
        return " ".join(part for part in (self.first_name, self.last_name) if part)
