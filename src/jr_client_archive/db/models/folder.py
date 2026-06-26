from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from jr_client_archive.db.base import Base
from jr_client_archive.db.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from jr_client_archive.db.models.client import Client
    from jr_client_archive.db.models.document import Document


class Folder(TimestampMixin, Base):
    """A node in a client's document folder tree (the physical filesystem
    mirror lives under ``AppPaths.archive_root / folder_relative_path``).
    """

    __tablename__ = "folders"

    id: Mapped[int] = mapped_column(primary_key=True)

    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), index=True
    )
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("folders.id", ondelete="CASCADE"), index=True
    )

    name: Mapped[str] = mapped_column(String(256))

    # Relative to AppPaths.archive_root. The watchdog sync service keeps
    # this in lockstep with the real folder on disk after renames/moves.
    relative_path: Mapped[str] = mapped_column(String(1024), unique=True)

    is_auto_generated: Mapped[bool] = mapped_column(Boolean, default=False)

    client: Mapped["Client"] = relationship(back_populates="folders")
    parent: Mapped["Folder | None"] = relationship(
        back_populates="children", remote_side=[id]
    )
    children: Mapped[list["Folder"]] = relationship(
        back_populates="parent", cascade="all, delete-orphan"
    )
    documents: Mapped[list["Document"]] = relationship(back_populates="folder")
