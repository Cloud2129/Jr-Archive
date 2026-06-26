"""DTO for the license/demo feature (Fase 8)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class LicenseStatus(BaseModel):
    is_activated: bool
    licensee: str | None
    first_launch_at: datetime
    demo_expires_at: datetime
    days_remaining: int
    is_demo_expired: bool
    is_read_only: bool
    max_demo_clients: int
    client_limit_reached: bool
