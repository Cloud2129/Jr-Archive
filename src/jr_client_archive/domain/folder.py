from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FolderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    parent_id: int | None
    name: str
    relative_path: str
    is_auto_generated: bool
    created_at: datetime
    updated_at: datetime
