"""Confirms which client a dropped document belongs to.

Shown after the drag&drop recognition engine ranks candidate clients for a
given filename. The user can accept a suggested candidate or fall back to
picking from the full client list by hand - the engine is a shortcut, never
a forced decision.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QVBoxLayout,
)

from jr_client_archive.application.client_queries import list_clients
from jr_client_archive.db.base import Database
from jr_client_archive.domain.client import ClientRead
from jr_client_archive.domain.client_match import ClientMatchRead


class DocumentMatchDialog(QDialog):
    def __init__(
        self, database: Database, filename: str, candidates: list[ClientMatchRead], parent=None
    ) -> None:
        super().__init__(parent)
        self._selected_client: ClientRead | None = candidates[0].client if candidates else None

        self.setWindowTitle("A quale cliente appartiene questo documento?")
        self.resize(420, 420)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Documento: {filename}"))

        layout.addWidget(QLabel("Suggerimenti automatici:"))
        self._suggestions_list = QListWidget()
        for candidate in candidates:
            item = QListWidgetItem(f"{candidate.client.display_name} ({candidate.reason}, {candidate.score:.0f}%)")
            item.setData(Qt.ItemDataRole.UserRole, candidate.client)
            self._suggestions_list.addItem(item)
        if not candidates:
            self._suggestions_list.addItem("Nessuna corrispondenza automatica trovata.")
        else:
            self._suggestions_list.setCurrentRow(0)
        self._suggestions_list.itemClicked.connect(self._on_suggestion_clicked)
        layout.addWidget(self._suggestions_list)

        layout.addWidget(QLabel("Oppure scegli manualmente:"))
        self._all_clients_list = QListWidget()
        for client in list_clients(database):
            item = QListWidgetItem(client.display_name)
            item.setData(Qt.ItemDataRole.UserRole, client)
            self._all_clients_list.addItem(item)
        self._all_clients_list.itemClicked.connect(self._on_manual_clicked)
        layout.addWidget(self._all_clients_list)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_suggestion_clicked(self, item: QListWidgetItem) -> None:
        client = item.data(Qt.ItemDataRole.UserRole)
        if client is not None:
            self._selected_client = client

    def _on_manual_clicked(self, item: QListWidgetItem) -> None:
        self._selected_client = item.data(Qt.ItemDataRole.UserRole)

    def _on_accept(self) -> None:
        if self._selected_client is None:
            QMessageBox.warning(self, "Cliente non selezionato", "Seleziona un cliente prima di continuare.")
            return
        self.accept()

    def selected_client(self) -> ClientRead | None:
        return self._selected_client
