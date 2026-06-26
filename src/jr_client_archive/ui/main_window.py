"""Phase 1 shell of the main dashboard.

Proves the full stack (Qt -> application layer -> repository -> SQLite) is
wired correctly. Client CRUD, drag&drop, "documents to verify" and the
statistics panel are deliberately out of scope here and arrive in later
phases - this window only lists/searches existing clients.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from jr_client_archive import APP_NAME, __version__
from jr_client_archive.application.client_queries import list_clients, search_clients
from jr_client_archive.config.paths import AppPaths
from jr_client_archive.db.base import Database


class MainWindow(QMainWindow):
    def __init__(self, database: Database, paths: AppPaths) -> None:
        super().__init__()
        self._database = database
        self._paths = paths

        self.setWindowTitle(APP_NAME)
        self.resize(960, 640)

        self._search_box = QLineEdit(placeholderText="Cerca cliente per nome, codice, C.F., P.IVA...")
        self._search_box.textChanged.connect(self._on_search_changed)

        self._client_list = QListWidget()

        new_client_button = QPushButton("Nuovo cliente")
        new_client_button.clicked.connect(self._on_new_client_clicked)

        layout = QVBoxLayout()
        layout.addWidget(self._search_box)
        layout.addWidget(self._client_list)
        layout.addWidget(new_client_button)

        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

        self.statusBar().addWidget(QLabel(f"v{__version__} | Archivio: {paths.root}"))

        self._reload_clients()

    def _reload_clients(self) -> None:
        clients = list_clients(self._database)
        self._populate(clients)

    def _on_search_changed(self, term: str) -> None:
        clients = search_clients(self._database, term)
        self._populate(clients)

    def _populate(self, clients) -> None:
        self._client_list.clear()
        if not clients:
            self._client_list.addItem("Nessun cliente. Trascina un documento o crea un nuovo cliente.")
            return
        for client in clients:
            self._client_list.addItem(f"{client.client_code} - {client.display_name}")

    def _on_new_client_clicked(self) -> None:
        QMessageBox.information(
            self,
            "Nuovo cliente",
            "La gestione completa dei clienti arriva nella Fase 2.",
        )
