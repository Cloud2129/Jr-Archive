from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from jr_client_archive.db.base import Base
from jr_client_archive.db.models.mixins import TimestampMixin


class AppSettingRow(TimestampMixin, Base):
    """Key/value store backing every user-editable setting.

    The requirement is explicit: no manual JSON editing, everything
    changeable from the UI. Storing settings as DB rows means the settings
    screen (a future phase) is just CRUD on this table, and
    ``config.settings.SettingsService`` is the only place that knows how to
    turn rows into a typed ``AppSettings`` object.
    """

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value_json: Mapped[str] = mapped_column(Text)
