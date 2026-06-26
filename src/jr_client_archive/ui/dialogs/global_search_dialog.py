"""Fase 6 - ricerca globale: una sola barra di ricerca per clienti e
documenti di tutto l'archivio.

Mostra due liste separate (i risultati clienti dalla LIKE su
``ClientRepository.search``, i risultati documenti dall'indice FTS5 - vedi
``application.global_search_queries``). Il doppio click su un risultato
apre direttamente il fascicolo del cliente corrispondente; per un
documento, il fascicolo si apre con quel documento già selezionato e in
anteprima, cosa che ``ClientDossierDialog`` supporta tramite
``select_document_id``.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)

from jr_client_archive.application.client_queries import get_client
from jr_client_archive.application.global_search_queries import global_search
from jr_client_archive.db.base import Database
from jr_client_archive.domain.client import ClientRead
from jr_client_archive.domain.document import DocumentRead
from jr_client_archive.ui.dialogs.client_dossier_dialog import ClientDossierDialog


class GlobalSearchDialog(QDialog):
    def __init__(self, database: Database, *, username: str, parent=None) -> None:
        super().__init__(parent)
        self._database = database
        self._username = username

        self.setWindowTitle("Ricerca globale")
        self.resize(640, 480)

        self._search_box = QLineEdit(placeholderText="Cerca tra clienti e documenti...")
        self._search_box.textChanged.connect(self._on_search_changed)

        self._client_results = QListWidget()
        self._client_results.itemDoubleClicked.connect(self._on_client_result_double_clicked)

        self._document_results = QListWidget()
        self._document_results.itemDoubleClicked.connect(self._on_document_result_double_clicked)

        columns = QHBoxLayout()
        clients_column = QVBoxLayout()
        clients_column.addWidget(QLabel("Clienti"))
        clients_column.addWidget(self._client_results)
        documents_column = QVBoxLayout()
        documents_column.addWidget(QLabel("Documenti"))
        documents_column.addWidget(self._document_results)
        columns.addLayout(clients_column)
        columns.addLayout(documents_column)

        layout = QVBoxLayout(self)
        layout.addWidget(self._search_box)
        layout.addLayout(columns)

        self._search_box.setFocus()

    def _on_search_changed(self, term: str) -> None:
        self._client_results.clear()
        self._document_results.clear()
        if not term.strip():
            return

        result = global_search(self._database, term)

        if not result.clients:
            self._client_results.addItem("Nessun cliente trovato.")
        for client in result.clients:
            item = QListWidgetItem(f"{client.client_code} - {client.display_name}")
            item.setData(Qt.ItemDataRole.UserRole, client)
            self._client_results.addItem(item)

        if not result.documents:
            self._document_results.addItem("Nessun documento trovato.")
        for document in result.documents:
            client = get_client(self._database, document.client_id)
            client_label = client.display_name if client else "?"
            item = QListWidgetItem(f"{client_label} - {document.original_filename}")
            item.setData(Qt.ItemDataRole.UserRole, document)
            self._document_results.addItem(item)

    def _on_client_result_double_clicked(self, item: QListWidgetItem) -> None:
        client = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(client, ClientRead):
            return
        self._open_dossier(client)

    def _on_document_result_double_clicked(self, item: QListWidgetItem) -> None:
        document = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(document, DocumentRead):
            return
        client = get_client(self._database, document.client_id)
        if client is None:
            return
        self._open_dossier(client, select_document_id=document.id)

    def _open_dossier(self, client: ClientRead, *, select_document_id: int | None = None) -> None:
        dialog = ClientDossierDialog(
            self._database,
            client,
            username=self._username,
            parent=self,
            select_document_id=select_document_id,
        )
        dialog.exec()
