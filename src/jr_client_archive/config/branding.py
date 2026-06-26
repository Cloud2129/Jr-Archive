"""JR Solutions brand identity constants.

Centralizes the official palette/claim so every part of the UI (qt-material
theme, status colors, window chrome) draws from the same source instead of
hardcoding hex values in multiple places.
"""

from __future__ import annotations

from pathlib import Path

BRAND_NAME = "JR Solutions"
BRAND_CLAIM = "Efficiency Through Innovation"

COLOR_PRIMARY = "#17375E"
COLOR_SECONDARY = "#2F5597"
COLOR_ACCENT = "#5B9BD5"
COLOR_SUCCESS = "#70AD47"
COLOR_WARNING = "#ED7D31"
COLOR_ERROR = "#C00000"
COLOR_BACKGROUND = "#F3F6F9"
COLOR_TEXT = "#202124"

THEME_NAME = "jr_solutions"
THEME_FILE = Path(__file__).resolve().parent.parent / "resources" / "themes" / "jr_solutions.xml"
