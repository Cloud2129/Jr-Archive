"""'Nuovo cliente' dialog.

Collects the anagrafica plus whatever custom fields are configured for
CLIENT, then delegates the actual creation (DB row + physical folder + audit
entry) to ``application.client_commands.create_client`` - this dialog only
gathers input and shows errors, it owns no business logic.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QVBoxLayout,
)

from jr_client_archive.application.client_commands import CreateClientRequest, create_client
from jr_client_archive.application.custom_field_queries import list_definitions
from jr_client_archive.db.base import Database
from jr_client_archive.domain.client import ClientCreate, ClientRead
from jr_client_archive.domain.enums import ClientType, EntityType
from jr_client_archive.ui.widgets.custom_field_form import CustomFieldFormWidget


class NewClientDialog(QDialog):
    def __init__(self, database: Database, *, username: str, parent=None) -> None:
        super().__init__(parent)
        self._database = database
        self._username = username
        self.created_client: ClientRead | None = None

        self.setWindowTitle("Nuovo cliente")
        self.resize(420, 480)

        self._client_type = QComboBox()
        self._client_type.addItem("Persona fisica", ClientType.PERSON)
        self._client_type.addItem("Azienda", ClientType.COMPANY)

        self._first_name = QLineEdit()
        self._last_name = QLineEdit()
        self._company_name = QLineEdit()
        self._fiscal_code = QLineEdit()
        self._vat_number = QLineEdit()
        self._practice_number = QLineEdit()
        self._email = QLineEdit()
        self._phone = QLineEdit()
        self._notes = QPlainTextEdit()

        anagrafica_layout = QFormLayout()
        anagrafica_layout.addRow("Tipo cliente", self._client_type)
        anagrafica_layout.addRow("Nome", self._first_name)
        anagrafica_layout.addRow("Cognome", self._last_name)
        anagrafica_layout.addRow("Ragione sociale", self._company_name)
        anagrafica_layout.addRow("Codice fiscale", self._fiscal_code)
        anagrafica_layout.addRow("Partita IVA", self._vat_number)
        anagrafica_layout.addRow("Numero pratica", self._practice_number)
        anagrafica_layout.addRow("Email", self._email)
        anagrafica_layout.addRow("Telefono", self._phone)
        anagrafica_layout.addRow("Note", self._notes)

        definitions = list_definitions(database, EntityType.CLIENT)
        self._custom_field_form = CustomFieldFormWidget(definitions)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(anagrafica_layout)
        layout.addWidget(self._custom_field_form)
        layout.addWidget(buttons)

    def _on_accept(self) -> None:
        client_type = self._client_type.currentData()
        if client_type == ClientType.COMPANY and not self._company_name.text().strip():
            QMessageBox.warning(self, "Dati incompleti", "Indicare la ragione sociale.")
            return
        if client_type == ClientType.PERSON and not (self._first_name.text().strip() or self._last_name.text().strip()):
            QMessageBox.warning(self, "Dati incompleti", "Indicare almeno nome o cognome.")
            return

        error = self._custom_field_form.validate()
        if error:
            QMessageBox.warning(self, "Dati incompleti", error)
            return

        client_payload = ClientCreate(
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
        request = CreateClientRequest(client=client_payload, custom_field_values=self._custom_field_form.values())

        try:
            self.created_client = create_client(self._database, request, username=self._username)
        except Exception as exc:
            QMessageBox.critical(self, "Errore", f"Impossibile creare il cliente:\n{exc}")
            return

        self.accept()
