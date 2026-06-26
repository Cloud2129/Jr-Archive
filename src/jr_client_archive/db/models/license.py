from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from jr_client_archive.db.base import Base


class LicenseStateRow(Base):
    """Single-row table (``id`` is always ``1``): when the app was first
    launched - the start of the demo clock, set once and never touched
    again - and, once activated, the signed license key that lifts every
    demo limit.
    """

    __tablename__ = "license_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_launch_at: Mapped[datetime] = mapped_column(DateTime)
    license_key: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
