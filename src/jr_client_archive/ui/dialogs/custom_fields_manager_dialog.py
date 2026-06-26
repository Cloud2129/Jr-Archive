"""'Campi personalizzati' management screen.

Every button here maps to one function in
``application.custom_field_commands`` - this dialog never touches a
repository or the database directly, it only refreshes its list from
``list_definitions`` after each action.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from jr_client_archive.application.custom_field_commands import (
    create_definition,
    delete_definition,
    move_definition,
    update_definition,
)
from jr_client_archive.application.custom_field_queries import list_definitions
from jr_client_archive.db.base import Database
from jr_client_archive.domain.custom_field import (
    CustomFieldDefinitionCreate,
    CustomFieldDefinitionRead,
    CustomFieldDefinitionUpdate,
)
from jr_client_archive.domain.enums import CustomFieldType, EntityType


class CustomFieldsManagerDialog(QDialog):
    def __init__(self, database: Database, entity_type: EntityType, *, username: str, parent=None) -> None:
        super().__init__(parent)
        self._database = database
        self._entity_type = entity_type
        self._username = username

        self.setWindowTitle("Campi personalizzati")
        self.resize(480, 420)

        self._list = QListWidget()

        add_button = QPushButton("Aggiungi...")
        edit_button = QPushButton("Modifica...")
        delete_button = QPushButton("Elimina")
        up_button = QPushButton("Su")
        down_button = QPushButton("Giu")

        add_button.clicked.connect(self._on_add)
        edit_button.clicked.connect(self._on_edit)
        delete_button.clicked.connect(self._on_delete)
        up_button.clicked.connect(lambda: self._on_move("up"))
        down_button.clicked.connect(lambda: self._on_move("down"))

        buttons_layout = QHBoxLayout()
        for button in (add_button, edit_button, delete_button, up_button, down_button):
            buttons_layout.addWidget(button)

        close_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_box.rejected.connect(self.reject)
        close_box.accepted.connect(self.accept)
        close_box.button(QDialogButtonBox.StandardButton.Close).clicked.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addWidget(self._list)
        layout.addLayout(buttons_layout)
        layout.addWidget(close_box)

        self._reload()

    def _reload(self) -> None:
        self._list.clear()
        for definition in list_definitions(self._database, self._entity_type):
            label = definition.label + (" *" if definition.is_required else "")
            item = QListWidgetItem(f"{label} ({definition.field_type.value})")
            item.setData(Qt.ItemDataRole.UserRole, definition)
            self._list.addItem(item)

    def _selected_definition(self) -> CustomFieldDefinitionRead | None:
        item = self._list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _on_add(self) -> None:
        dialog = _FieldEditDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            create_definition(
                self._database,
                CustomFieldDefinitionCreate(
                    entity_type=self._entity_type,
                    field_key=dialog.field_key(),
                    label=dialog.label(),
                    field_type=dialog.field_type(),
                    is_required=dialog.is_required(),
                    choices=dialog.choices(),
                ),
                username=self._username,
            )
        except Exception as exc:
            QMessageBox.critical(self, "Errore", f"Impossibile creare il campo:\n{exc}")
            return
        self._reload()

    def _on_edit(self) -> None:
        definition = self._selected_definition()
        if definition is None:
            return
        dialog = _FieldEditDialog(self, definition=definition, lock_type_and_key=True)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            update_definition(
                self._database,
                definition.id,
                CustomFieldDefinitionUpdate(
                    label=dialog.label(), is_required=dialog.is_required(), choices=dialog.choices()
                ),
                username=self._username,
            )
        except Exception as exc:
            QMessageBox.critical(self, "Errore", f"Impossibile modificare il campo:\n{exc}")
            return
        self._reload()

    def _on_delete(self) -> None:
        definition = self._selected_definition()
        if definition is None:
            return
        reply = QMessageBox.question(
            self,
            "Elimina campo",
            f"Eliminare il campo '{definition.label}'? I valori salvati per questo campo verranno persi.",
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        delete_definition(self._database, definition.id, username=self._username)
        self._reload()

    def _on_move(self, direction: str) -> None:
        definition = self._selected_definition()
        if definition is None:
            return
        move_definition(self._database, definition.id, direction, username=self._username)
        self._reload()


class _FieldEditDialog(QDialog):
    """Small modal form for the field_key/label/type/required/choices quintet."""

    def __init__(
        self,
        parent,
        definition: CustomFieldDefinitionRead | None = None,
        lock_type_and_key: bool = False,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Campo personalizzato")

        self._field_key = QLineEdit(definition.field_key if definition else "")
        self._label = QLineEdit(definition.label if definition else "")
        self._field_type = QComboBox()
        for field_type in CustomFieldType:
            self._field_type.addItem(field_type.value, field_type)
        if definition:
            self._field_type.setCurrentIndex(self._field_type.findData(definition.field_type))
        self._is_required = QCheckBox()
        self._is_required.setChecked(definition.is_required if definition else False)
        self._choices = QLineEdit(", ".join(definition.choices) if definition and definition.choices else "")

        if lock_type_and_key:
            self._field_key.setEnabled(False)
            self._field_type.setEnabled(False)

        form = QFormLayout()
        form.addRow("Chiave (univoca)", self._field_key)
        form.addRow("Etichetta", self._label)
        form.addRow("Tipo", self._field_type)
        form.addRow("Obbligatorio", self._is_required)
        form.addRow("Opzioni (solo per Lista, separate da virgola)", self._choices)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _on_accept(self) -> None:
        if not self._field_key.text().strip() or not self._label.text().strip():
            QMessageBox.warning(self, "Dati incompleti", "Chiave ed etichetta sono obbligatorie.")
            return
        if self.field_type() == CustomFieldType.CHOICE and not self.choices():
            QMessageBox.warning(self, "Dati incompleti", "Un campo di tipo Lista richiede almeno un'opzione.")
            return
        self.accept()

    def field_key(self) -> str:
        return self._field_key.text().strip()

    def label(self) -> str:
        return self._label.text().strip()

    def field_type(self) -> CustomFieldType:
        return self._field_type.currentData()

    def is_required(self) -> bool:
        return self._is_required.isChecked()

    def choices(self) -> list[str] | None:
        raw = [part.strip() for part in self._choices.text().split(",") if part.strip()]
        return raw or None
