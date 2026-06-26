"""Process-wide logging bootstrap.

This configures the *technical* log (rotating files on disk, for diagnostics
and crash forensics). The separate, queryable *business* audit trail
("ogni accesso, ogni modifica, ogni rinomina...") lives in the database via
``jr_client_archive.services.audit_service`` and is a different concern on
purpose: one is for developers debugging a crash, the other is for an end
user asking "who touched this client last week".
"""

from __future__ import annotations

import logging
import logging.handlers

from jr_client_archive.config.paths import AppPaths

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_MAX_BYTES = 5 * 1024 * 1024
_BACKUP_COUNT = 5

_configured = False


def configure_logging(paths: AppPaths, *, level: int = logging.INFO) -> None:
    """Idempotently configure the root logger. Safe to call multiple times."""
    global _configured
    if _configured:
        return

    root = logging.getLogger()
    root.setLevel(level)

    formatter = logging.Formatter(_LOG_FORMAT)

    file_handler = logging.handlers.RotatingFileHandler(
        paths.logs_dir / "jr_client_archive.log",
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    _configured = True
