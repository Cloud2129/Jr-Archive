"""Typed, user-editable application settings.

Persisted as rows in the ``app_settings`` table (key -> JSON value), never
as a file the user could hand-edit. ``AppSettings`` is the one place that
knows the full set of *known* settings and their defaults; adding a new
setting is a one-line change here, not a schema migration.
"""

from __future__ import annotations

import json

from pydantic import BaseModel
from sqlalchemy.orm import Session

from jr_client_archive.db.models.setting import AppSettingRow


class AppSettings(BaseModel):
    theme: str = "jr_solutions"
    default_username: str = "utente"
    log_level: str = "INFO"
    document_naming_pattern: str = "{client_code}_{last_name}_{first_name}_{document_type}_{document_date}"


class SettingsService:
    """Reads/writes :class:`AppSettings` through the database session."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def load(self) -> AppSettings:
        rows = self._session.query(AppSettingRow).all()
        raw = {row.key: json.loads(row.value_json) for row in rows}
        return AppSettings.model_validate(raw)

    def save(self, settings: AppSettings) -> None:
        for key, value in settings.model_dump().items():
            row = self._session.get(AppSettingRow, key)
            value_json = json.dumps(value)
            if row is None:
                row = AppSettingRow(key=key, value_json=value_json)
                self._session.add(row)
            else:
                row.value_json = value_json
        self._session.commit()
