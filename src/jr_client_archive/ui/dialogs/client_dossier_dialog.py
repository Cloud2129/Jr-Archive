"""'Fascicolo cliente' - view and edit one client.

Documents, preview and history are deliberately out of scope here: they
belong to Fase 3 (Gestione documenti). This dialog covers anagrafica,
custom fields, notes, timestamps and the folder tree only.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from jr_client_archive.application.client_commands import update_client
from jr_client_archive.application.custom_field_queries import get_values_for_entity, list_definitions
from jr_client_archive.application.folder_commands import create_subfolder
from jr_client_archive.application.folder_queries import list_folders_for_client
from jr_client_archive.db.base import Database
from jr_client_archive.domain.client import ClientRead, ClientUpdate
from jr_client_archive.domain.enums import ClientType, EntityType
from jr_client_archive.domain.folder import FolderRead
from jr_client_archive.ui.widgets.custom_field_form import CustomFieldFormWidget


class ClientDossierDialog(QDialog):
    def __init__(self, database: Database, client: ClientRead, *, username: str, parent=None) -> None:
        super().__init__(parent)
        self._database = database
        self._client = client
        self._username = username

        self.setWindowTitle(f"Fascicolo - {client.display_name}")
        self.resize(560, 640)

        layout = QVBoxLayout(self)
        layout.addWidget(self._build_anagrafica_section())
        layout.addWidget(self._build_custom_fields_section())
        layout.addWidget(self._build_folder_section())
        layout.addWidget(self._build_timestamps_section())

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Close)
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.accept)
        layout.addWidget(buttons)

    def _build_anagrafica_section(self) -> QWidget:
        client = self._client

        self._client_type = QComboBox()
        self._client_type.addItem("Persona fisica", ClientType.PERSON)
        self._client_type.addItem("Azienda", ClientType.COMPANY)
        self._client_type.setCurrentIndex(self._client_type.findData(client.client_type))

        self._first_name = QLineEdit(client.first_name or "")
        self._last_name = QLineEdit(client.last_name or "")
        self._company_name = QLineEdit(client.company_name or "")
        self._fiscal_code = QLineEdit(client.fiscal_code or "")
        self._vat_number = QLineEdit(client.vat_number or "")
        self._practice_number = QLineEdit(client.practice_number or "")
        self._email = QLineEdit(client.email or "")
        self._phone = QLineEdit(client.phone or "")
        self._notes = QPlainTextEdit(client.notes or "")

        form = QFormLayout()
        form.addRow("Codice cliente", QLabel(client.client_code))
        form.addRow("Tipo cliente", self._client_type)
        form.addRow("Nome", self._first_name)
        form.addRow("Cognome", self._last_name)
        form.addRow("Ragione sociale", self._company_name)
        form.addRow("Codice fiscale", self._fiscal_code)
        form.addRow("Partita IVA", self._vat_number)
        form.addRow("Numero pratica", self._practice_number)
        form.addRow("Email", self._email)
        form.addRow("Telefono", self._phone)
        form.addRow("Note", self._notes)

        widget = QWidget()
        widget.setLayout(form)
        return widget

    def _build_custom_fields_section(self) -> QWidget:
        definitions = list_definitions(self._database, EntityType.CLIENT)
        values = get_values_for_entity(self._database, EntityType.CLIENT, self._client.id)
        self._custom_field_form = CustomFieldFormWidget(definitions, values)
        return self._custom_field_form

    def _build_folder_section(self) -> QWidget:
        self._folder_tree = QTreeWidget()
        self._folder_tree.setHeaderLabels(["Cartelle"])
        self._reload_folders()

        new_subfolder_button = QPushButton("Nuova sottocartella")
        new_subfolder_button.clicked.connect(self._on_new_subfolder)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Cartelle dell'archivio"))
        layout.addWidget(self._folder_tree)
        layout.addWidget(new_subfolder_button)

        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def _reload_folders(self) -> None:
        self._folder_tree.clear()
        folders = list_folders_for_client(self._database, self._client.id)
        items_by_id: dict[int, QTreeWidgetItem] = {}

        remaining = list(folders)
        while remaining:
            progressed = False
            for folder in list(remaining):
                if folder.parent_id is None:
                    item = QTreeWidgetItem([folder.name])
                    item.setData(0, Qt.ItemDataRole.UserRole, folder)
                    self._folder_tree.addTopLevelItem(item)
                    items_by_id[folder.id] = item
                    remaining.remove(folder)
                    progressed = True
                elif folder.parent_id in items_by_id:
                    item = QTreeWidgetItem([folder.name])
                    item.setData(0, Qt.ItemDataRole.UserRole, folder)
                    items_by_id[folder.parent_id].addChild(item)
                    items_by_id[folder.id] = item
                    remaining.remove(folder)
                    progressed = True
            if not progressed:
                break
        self._folder_tree.expandAll()

    def _build_timestamps_section(self) -> QWidget:
        client = self._client
        label = QLabel(f"Creato: {client.created_at:%d/%m/%Y %H:%M}    Aggiornato: {client.updated_at:%d/%m/%Y %H:%M}")
        return label

    def _selected_folder(self) -> FolderRead | None:
        item = self._folder_tree.currentItem()
        return item.data(0, Qt.ItemDataRole.UserRole) if item else None

    def _on_new_subfolder(self) -> None:
        parent_folder = self._selected_folder()
        if parent_folder is None:
            QMessageBox.information(self, "Nuova sottocartella", "Seleziona prima la cartella padre.")
            return
        name, ok = QInputDialog.getText(self, "Nuova sottocartella", "Nome cartella:")
        if not ok or not name.strip():
            return
        try:
            create_subfolder(self._database, self._client.id, parent_folder.id, name.strip(), username=self._username)
        except Exception as exc:
            QMessageBox.critical(self, "Errore", f"Impossibile creare la cartella:\n{exc}")
            return
        self._reload_folders()

    def _on_save(self) -> None:
        client_type = self._client_type.currentData()
        error = self._custom_field_form.validate()
        if error:
            QMessageBox.warning(self, "Dati incompleti", error)
            return

        payload = ClientUpdate(
            client_type=client_type,
            first_name=self._first_name.text().strip() or None,
            last_name=self._last_name.text().strip() or None,
            company_name=self._company_name.text().strip() or None,
            fiscal_code=self._fiscal_code.text().strip() or None,
            vat_number=self._vat_number.text().strip() or None,
            practice_number=self._practice_number.text().strip() or None,
            email=self._email.text().strip() or None,
            phone=self._phone.text().strip() or None,
            notes=self._notes.toPlainText().strip() or None,
        )
        try:
            self._client = update_client(
                self._database, self._client.id, payload, self._custom_field_form.values(), username=self._username
            )
        except Exception as exc:
            QMessageBox.critical(self, "Errore", f"Impossibile salvare il cliente:\n{exc}")
            return
        self.accept()
