"""DTOs for the backup/restore feature (Fase 7)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel


class BackupInfo(BaseModel):
    path: Path
    created_at: datetime
    size_bytes: int


class RestoreResult(BaseModel):
    safety_backup_dir: Path
