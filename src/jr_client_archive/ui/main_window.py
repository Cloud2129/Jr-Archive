"""Main dashboard.

Lists/searches clients, creates new ones, opens the dossier on
double-click, and gives access to the custom-fields manager. Also accepts
documents dropped directly onto the window: the drag&drop recognition
engine suggests a client, the user confirms (or picks one by hand), and the
document lands in that client's root folder as ``TO_VERIFY`` - same place
the "documenti da verificare" panel below pulls from. This window owns no
business logic, it only calls into ``application`` and reflects the
result.

It also (optionally - see ``start_external_sync``) hosts the watchdog
filesystem watcher that keeps the database in sync when a document/folder
gets renamed or moved outside the app. The watcher's callback runs on a
background thread, so it only ever talks to this window through a
``QObject`` signal: Qt automatically queues a cross-thread signal emission
onto the receiver's thread, which is what lets ``_on_external_move`` use
the database/UI exactly like every other slot here, with no extra locking.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from jr_client_archive import APP_NAME, __version__
from jr_client_archive.application.client_matching_queries import match_clients_for_filename
from jr_client_archive.application.client_queries import (
    count_active_clients,
    get_client,
    list_clients,
    search_clients,
)
from jr_client_archive.application.document_commands import add_document
from jr_client_archive.application.document_queries import list_documents_to_verify
from jr_client_archive.application.external_sync_commands import reconcile_external_move
from jr_client_archive.application.folder_queries import get_root_folder
from jr_client_archive.application.license_queries import get_license_status
from jr_client_archive.config import branding
from jr_client_archive.config.paths import AppPaths
from jr_client_archive.db.base import Database
from jr_client_archive.domain.enums import EntityType
from jr_client_archive.services.folder_watch_service import FolderWatchService
from jr_client_archive.ui.dialogs.backup_dialog import BackupDialog
from jr_client_archive.ui.dialogs.client_dossier_dialog import ClientDossierDialog
from jr_client_archive.ui.dialogs.custom_fields_manager_dialog import CustomFieldsManagerDialog
from jr_client_archive.ui.dialogs.document_match_dialog import DocumentMatchDialog
from jr_client_archive.ui.dialogs.global_search_dialog import GlobalSearchDialog
from jr_client_archive.ui.dialogs.license_dialog import LicenseDialog
from jr_client_archive.ui.dialogs.new_client_dialog import NewClientDialog
from jr_client_archive.utils.current_user import get_current_username

logger = logging.getLogger(__name__)


class _ExternalSyncBridge(QObject):
    """Lives on the main thread; the watchdog thread only ever calls
    ``moved.emit`` on it, never touches the database or any widget."""

    moved = Signal(str, str, bool)


class MainWindow(QMainWindow):
    def __init__(self, database: Database, paths: AppPaths) -> None:
        super().__init__()
        self._database = database
        self._paths = paths
        self._username = get_current_username()
        self._folder_watch_service: FolderWatchService | None = None

        self.setWindowTitle(f"{APP_NAME} - {branding.BRAND_CLAIM}")
        self.resize(960, 640)
        self.setAcceptDrops(True)

        self._search_box = QLineEdit(placeholderText="Cerca cliente per nome, codice, C.F., P.IVA...")
        self._search_box.textChanged.connect(self._on_search_changed)

        self._client_list = QListWidget()
        self._client_list.itemDoubleClicked.connect(self._on_client_double_clicked)

        new_client_button = QPushButton("Nuovo cliente")
        new_client_button.clicked.connect(self._on_new_client_clicked)

        custom_fields_button = QPushButton("Campi personalizzati...")
        custom_fields_button.clicked.connect(self._on_custom_fields_clicked)

        global_search_button = QPushButton("Ricerca globale (Ctrl+F)")
        global_search_button.clicked.connect(self._on_global_search_clicked)
        global_search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        global_search_shortcut.activated.connect(self._on_global_search_clicked)

        backup_button = QPushButton("Backup e ripristino...")
        backup_button.clicked.connect(self._on_backup_clicked)

        license_button = QPushButton("Licenza...")
        license_button.clicked.connect(self._on_license_clicked)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(new_client_button)
        buttons_layout.addWidget(custom_fields_button)
        buttons_layout.addWidget(global_search_button)
        buttons_layout.addWidget(backup_button)
        buttons_layout.addWidget(license_button)

        self._license_banner = QLabel()
        self._license_banner.setWordWrap(True)

        self._stats_label = QLabel()

        self._to_verify_list = QListWidget()
        self._to_verify_list.itemDoubleClicked.connect(self._on_to_verify_double_clicked)

        layout = QVBoxLayout()
        layout.addWidget(self._license_banner)
        layout.addWidget(self._search_box)
        layout.addWidget(self._client_list)
        layout.addLayout(buttons_layout)
        layout.addWidget(self._stats_label)
        layout.addWidget(QLabel("Documenti da verificare"))
        layout.addWidget(self._to_verify_list)

        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

        self.statusBar().addWidget(QLabel(f"{branding.BRAND_NAME} | v{__version__} | Archivio: {paths.root}"))

        self._reload_clients()
        self._reload_to_verify()

    def _reload_clients(self) -> None:
        clients = list_clients(self._database)
        self._populate(clients)
        self._stats_label.setText(f"Clienti attivi: {count_active_clients(self._database)}")
        self._reload_license_banner()

    def _reload_license_banner(self) -> None:
        status = get_license_status(self._database)
        if status.is_activated:
            self._license_banner.setText("")
            self._license_banner.setVisible(False)
            return
        self._license_banner.setVisible(True)
        if status.is_demo_expired:
            self._license_banner.setText(
                "Versione demo scaduta - sola lettura. Attiva una licenza per modificare i dati."
            )
        else:
            self._license_banner.setText(
                f"Versione demo - {status.days_remaining} giorni rimanenti "
                f"(max {status.max_demo_clients} clienti)."
            )

    def _reload_to_verify(self) -> None:
        self._to_verify_list.clear()
        documents = list_documents_to_verify(self._database)
        if not documents:
            self._to_verify_list.addItem("Nessun documento da verificare.")
            return
        for document in documents:
            client = get_client(self._database, document.client_id)
            client_label = client.display_name if client else "?"
            item = QListWidgetItem(f"{client_label} - {document.original_filename}")
            item.setData(Qt.ItemDataRole.UserRole, document.client_id)
            self._to_verify_list.addItem(item)

    def _on_search_changed(self, term: str) -> None:
        clients = search_clients(self._database, term)
        self._populate(clients)

    def _populate(self, clients) -> None:
        self._client_list.clear()
        if not clients:
            self._client_list.addItem("Nessun cliente. Trascina un documento o crea un nuovo cliente.")
            return
        for client in clients:
            item = QListWidgetItem(f"{client.client_code} - {client.display_name}")
            item.setData(Qt.ItemDataRole.UserRole, client.id)
            self._client_list.addItem(item)

    def _on_new_client_clicked(self) -> None:
        dialog = NewClientDialog(self._database, username=self._username, parent=self)
        if dialog.exec():
            self._reload_clients()

    def _on_client_double_clicked(self, item: QListWidgetItem) -> None:
        client_id = item.data(Qt.ItemDataRole.UserRole)
        if client_id is None:
            return
        client = get_client(self._database, client_id)
        if client is None:
            return
        dialog = ClientDossierDialog(self._database, client, username=self._username, parent=self)
        dialog.exec()
        self._reload_clients()
        self._reload_to_verify()

    def _on_to_verify_double_clicked(self, item: QListWidgetItem) -> None:
        client_id = item.data(Qt.ItemDataRole.UserRole)
        if client_id is None:
            return
        client = get_client(self._database, client_id)
        if client is None:
            return
        dialog = ClientDossierDialog(self._database, client, username=self._username, parent=self)
        dialog.exec()
        self._reload_clients()
        self._reload_to_verify()

    def _on_custom_fields_clicked(self) -> None:
        dialog = CustomFieldsManagerDialog(self._database, EntityType.CLIENT, username=self._username, parent=self)
        dialog.exec()

    def _on_global_search_clicked(self) -> None:
        dialog = GlobalSearchDialog(self._database, username=self._username, parent=self)
        dialog.exec()
        self._reload_clients()
        self._reload_to_verify()

    def _on_backup_clicked(self) -> None:
        dialog = BackupDialog(self._database, username=self._username, parent=self)
        dialog.exec()
        if dialog.restored:
            self._reload_clients()
            self._reload_to_verify()

    def _on_license_clicked(self) -> None:
        dialog = LicenseDialog(self._database, username=self._username, parent=self)
        dialog.exec()
        self._reload_license_banner()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        for url in event.mimeData().urls():
            if not url.isLocalFile():
                continue
            path = Path(url.toLocalFile())
            if path.is_file():
                self._handle_dropped_file(path)
        event.acceptProposedAction()

    def _handle_dropped_file(self, path: Path) -> None:
        candidates = match_clients_for_filename(self._database, path.name)
        dialog = DocumentMatchDialog(self._database, path.name, candidates, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        client = dialog.selected_client()
        if client is None:
            return

        folder = get_root_folder(self._database, client.id)
        if folder is None:
            QMessageBox.critical(self, "Errore", "Cartella radice del cliente non trovata.")
            return
        try:
            add_document(self._database, client.id, folder.id, path, username=self._username)
        except Exception as exc:
            QMessageBox.critical(self, "Errore", f"Impossibile importare il documento:\n{exc}")
            return
        self._reload_to_verify()

    def start_external_sync(self) -> None:
        """Starts the watchdog filesystem watcher.

        Not called from ``__init__``: spinning up a real OS-level watcher
        is appropriate for the running application, never for tests that
        construct a ``MainWindow`` against a throwaway ``tmp_path``.
        """
        self._paths.archive_root.mkdir(parents=True, exist_ok=True)
        bridge = _ExternalSyncBridge(self)
        bridge.moved.connect(self._on_external_move)
        self._folder_watch_service = FolderWatchService(self._paths.archive_root, bridge.moved.emit)
        self._folder_watch_service.start()

    def _on_external_move(self, old_relative_path: str, new_relative_path: str, is_directory: bool) -> None:
        try:
            reconciled = reconcile_external_move(
                self._database, old_relative_path, new_relative_path, is_directory=is_directory
            )
        except Exception:
            logger.exception(
                "Sincronizzazione esterna non riuscita per '%s' -> '%s'", old_relative_path, new_relative_path
            )
            return
        if reconciled:
            self._reload_clients()
            self._reload_to_verify()

    def closeEvent(self, event) -> None:
        if self._folder_watch_service is not None:
            self._folder_watch_service.stop()
        super().closeEvent(event)
