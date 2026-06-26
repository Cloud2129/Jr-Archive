"""Main dashboard.

Lists/searches clients, creates new ones, opens the dossier on
double-click, and gives access to the custom-fields manager. Drag&drop,
"documents to verify" and the full statistics panel still arrive in later
phases - this window owns no business logic, it only calls into
``application`` and reflects the result.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from jr_client_archive import APP_NAME, __version__
from jr_client_archive.application.client_queries import (
    count_active_clients,
    get_client,
    list_clients,
    search_clients,
)
from jr_client_archive.config import branding
from jr_client_archive.config.paths import AppPaths
from jr_client_archive.db.base import Database
from jr_client_archive.domain.enums import EntityType
from jr_client_archive.ui.dialogs.client_dossier_dialog import ClientDossierDialog
from jr_client_archive.ui.dialogs.custom_fields_manager_dialog import CustomFieldsManagerDialog
from jr_client_archive.ui.dialogs.new_client_dialog import NewClientDialog
from jr_client_archive.utils.current_user import get_current_username


class MainWindow(QMainWindow):
    def __init__(self, database: Database, paths: AppPaths) -> None:
        super().__init__()
        self._database = database
        self._paths = paths
        self._username = get_current_username()

        self.setWindowTitle(f"{APP_NAME} - {branding.BRAND_CLAIM}")
        self.resize(960, 640)

        self._search_box = QLineEdit(placeholderText="Cerca cliente per nome, codice, C.F., P.IVA...")
        self._search_box.textChanged.connect(self._on_search_changed)

        self._client_list = QListWidget()
        self._client_list.itemDoubleClicked.connect(self._on_client_double_clicked)

        new_client_button = QPushButton("Nuovo cliente")
        new_client_button.clicked.connect(self._on_new_client_clicked)

        custom_fields_button = QPushButton("Campi personalizzati...")
        custom_fields_button.clicked.connect(self._on_custom_fields_clicked)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(new_client_button)
        buttons_layout.addWidget(custom_fields_button)

        self._stats_label = QLabel()

        layout = QVBoxLayout()
        layout.addWidget(self._search_box)
        layout.addWidget(self._client_list)
        layout.addLayout(buttons_layout)
        layout.addWidget(self._stats_label)

        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

        self.statusBar().addWidget(QLabel(f"{branding.BRAND_NAME} | v{__version__} | Archivio: {paths.root}"))

        self._reload_clients()

    def _reload_clients(self) -> None:
        clients = list_clients(self._database)
        self._populate(clients)
        self._stats_label.setText(f"Clienti attivi: {count_active_clients(self._database)}")

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

    def _on_custom_fields_clicked(self) -> None:
        dialog = CustomFieldsManagerDialog(self._database, EntityType.CLIENT, username=self._username, parent=self)
        dialog.exec()
