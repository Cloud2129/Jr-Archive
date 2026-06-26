from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    """Adds ``created_at``/``updated_at``, maintained by the database itself.

    Using server-side defaults (rather than Python-side ``datetime.now()``)
    means the timestamp is correct even for rows inserted by a future tool
    (a migration script, a SQL console) that doesn't go through the ORM.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
