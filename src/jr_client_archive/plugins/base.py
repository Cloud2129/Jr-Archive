"""Plugin contract.

Future features explicitly called out as plugin candidates - local OCR,
TWAIN scanner input, digital signature, PEC, NAS sync, local AI - should
each become a class implementing this interface rather than being wired
directly into ``services``. Nothing in the application currently
discovers/loads plugins; this module only fixes the shape future plugins
must have so later phases don't need to revisit call sites.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class Plugin(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Stable, unique identifier for this plugin."""

    def on_load(self) -> None:
        """Called once when the plugin is activated. Override if needed."""

    def on_unload(self) -> None:
        """Called once when the plugin is deactivated. Override if needed."""
