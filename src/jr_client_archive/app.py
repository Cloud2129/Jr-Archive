"""Application entry point: wires config -> logging -> database -> UI."""

from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication

import jr_client_archive.db.models  # noqa: F401 - registers all ORM models
from jr_client_archive import APP_NAME, __version__
from jr_client_archive.config.logging_config import configure_logging
from jr_client_archive.config.paths import get_app_paths
from jr_client_archive.config.settings import SettingsService
from jr_client_archive.db.base import Database
from jr_client_archive.ui.main_window import MainWindow

logger = logging.getLogger(__name__)


def main() -> int:
    paths = get_app_paths()
    configure_logging(paths)
    logger.info("Avvio %s v%s - archivio: %s", APP_NAME, __version__, paths.root)

    database = Database(paths.database_file)
    database.create_all()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)

    _apply_theme(app, database)

    window = MainWindow(database=database, paths=paths)
    window.show()

    exit_code = app.exec()
    database.dispose()
    return exit_code


def _apply_theme(app: QApplication, database: Database) -> None:
    session = database.create_session()
    try:
        settings = SettingsService(session).load()
    finally:
        session.close()

    try:
        from qt_material import apply_stylesheet

        apply_stylesheet(app, theme=f"{settings.theme}.xml")
    except Exception:
        logger.warning("Tema qt-material non disponibile, uso lo stile predefinito.", exc_info=True)


if __name__ == "__main__":
    sys.exit(main())
